#!/usr/bin/env python3
"""
Gmail Sync Service for Alibaba Email Agent
Automatically fetches emails from various Alibaba service addresses
Uses Google Gemini AI for vendor analysis and quality scoring
Writes results to Google Sheets
"""

import os
import base64
import json
import sys
import argparse
import time
import email.utils
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import google.generativeai as genai
import gspread

# Simple .env loader if python-dotenv is not installed
def load_env_file(filepath='.env'):
    if os.path.exists(filepath):
        print(f"Loading environment from {filepath}...")
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
                        os.environ[key.strip()] = value.strip()

# Attempt to load local environment
load_env_file()

# Configuration
SHEET_ID = os.environ.get('SHEET_ID', '1kSWyTwYxiNYMG6IN_2GWcN4EBsVsTEmm1m_RTuIQ62o')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
TARGET_SENDERS = [
    'feedback@service.alibaba.com'
]
MAX_RESULTS_PER_PAGE = 50
GEMINI_RETRY_DELAY = 20 # increased to 20s to be safe
MAX_EMAILS_PER_RUN = 10 # Limit batch size to prevent long running jobs and rate limits

# OAuth Configuration
OAUTH_CLIENT_ID = os.environ.get('OAUTH_CLIENT_ID')
OAUTH_CLIENT_SECRET = os.environ.get('OAUTH_CLIENT_SECRET')
OAUTH_REFRESH_TOKEN = os.environ.get('OAUTH_REFRESH_TOKEN')

def get_gmail_service():
    """Create Gmail API service using OAuth refresh token"""
    if not all([OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_REFRESH_TOKEN]):
        raise ValueError(
            "OAuth credentials not found. Ensure OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, "
            "and OAUTH_REFRESH_TOKEN are set in your environment or .env file.\n"
            "See .env.example for the required format."
        )
    
    # Create credentials from refresh token
    creds = Credentials(
        token=None,
        refresh_token=OAUTH_REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=OAUTH_CLIENT_ID,
        client_secret=OAUTH_CLIENT_SECRET,
        scopes=['https://www.googleapis.com/auth/gmail.readonly']
    )
    
    # Refresh the access token
    try:
        print("Refreshing Gmail access token...")
        creds.refresh(Request())
    except Exception as e:
        print(f"Error refreshing token: {e}")
        raise
    
    # Build and return the Gmail service
    return build('gmail', 'v1', credentials=creds)

def get_sheets_service():
    """Create Google Sheets service using OAuth refresh token"""
    if not all([OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_REFRESH_TOKEN]):
        raise ValueError("OAuth credentials not found.")
    
    # Create credentials from refresh token
    creds = Credentials(
        token=None,
        refresh_token=OAUTH_REFRESH_TOKEN,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=OAUTH_CLIENT_ID,
        client_secret=OAUTH_CLIENT_SECRET,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    
    # Refresh the access token
    try:
        print("Refreshing Sheets access token...")
        creds.refresh(Request())
    except Exception as e:
        print(f"Error refreshing token: {e}")
        raise
    
    # Authorize gspread
    gc = gspread.authorize(creds)
    return gc

def analyze_with_gemini(email_body, email_subject):
    """Analyze email content using Google Gemini AI"""
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set. Skipping AI analysis.")
        return {
            "vendor": "Unknown (No API Key)",
            "summary": "AI Analysis skipped",
            "quality_score": 0
        }

    max_retries = 3
    retry_wait = 60 # Seconds to wait on 429

    for attempt in range(max_retries):
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Truncate body to avoid token limits
            max_body_len = 5000
            truncated_body = email_body[:max_body_len] + ("..." if len(email_body) > max_body_len else "")
            
            prompt = f"""
Analyze this Alibaba communication email and extract:
1. Vendor/Company Name (Look very carefully for the official company name, often found in the signature, footer, or after "From:" in the body, e.g., "Hangzhou Fuli Knitting Co.,ltd". If multiple names exist, pick the most specific vendor name.)
2. Brief Summary (1-2 sentences covering the core message, e.g., price quote, weekend notice, or order update)
3. Quality Score (1-10 based on professionalism and clarity)

Email Subject: {email_subject}
Email Body (Full Content): {truncated_body}

Respond ONLY in JSON format:
{{
    "vendor": "Full Company Name",
    "summary": "1-sentence summary",
    "quality_score": 8
}}
"""
            
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from markdown code blocks if present
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(result_text)
            return result
            
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                print(f"Rate limit hit. Waiting {retry_wait}s to retry (Attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_wait)
                continue
                
            print(f"Error analyzing with Gemini Code {attempt+1}: {e}")
            return {
                "vendor": "Unknown",
                "summary": "Analysis failed or rate limited",
                "quality_score": 0
            }

def process_single_message(gmail_service, sheet, msg_id, existing_ids):
    """Fetch and process a single message by ID"""
    if msg_id.lower() in existing_ids:
        print(f"Already processed: {msg_id}")
        return False

    try:
        message = gmail_service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        headers = message['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        
        body = ''
        if 'parts' in message['payload']:
            # Search for text/html first as it often contains the vendor name in the footer
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/html':
                    body_data = part['body'].get('data', '')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                        break
            # Fallback to text/plain if html not found
            if not body:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        body_data = part['body'].get('data', '')
                        if body_data:
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                            break
        else:
            body_data = message['payload']['body'].get('data', '')
            if body_data:
                body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')

        print(f"Analyzing: {subject}")
        # Extract sender for the sheet
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        
        # Extract actual email date from headers
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), None)
        if date_str:
            try:
                dt = email.utils.parsedate_to_datetime(date_str)
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        analysis = analyze_with_gemini(body, subject)
        
        row = [timestamp, msg_id, analysis['vendor'], analysis['summary'], analysis['quality_score'], subject, sender]
        sheet.append_row(row)
        existing_ids.add(msg_id.lower())
        print(f"Success: {analysis['vendor']} - Score: {analysis['quality_score']}")
        return True
    except Exception as e:
        print(f"Error processing message {msg_id}: {e}")
        return False

def fetch_and_process_emails(target_id=None):
    """Fetch emails from Gmail and process with AI"""
    if not SHEET_ID:
        raise ValueError("SHEET_ID configuration missing")

    try:
        print("Connecting to Services...")
        gmail_service = get_gmail_service()
        gc = get_sheets_service()
        
        print(f"Opening Sheet: {SHEET_ID}")
        sheet = gc.open_by_key(SHEET_ID).sheet1
        
        # Validate headers
        expected_headers = ['Timestamp', 'Email ID', 'Vendor', 'Summary', 'Quality Score', 'Subject', 'From']
        try:
            current_headers = sheet.row_values(1)
        except Exception:
            current_headers = []
            
        if not current_headers or current_headers[0] != 'Timestamp':
            print("Resetting sheet headers.")
            sheet.clear()
            sheet.append_row(expected_headers)

        # Existing IDs
        print("Fetching existing record IDs...")
        existing_data = sheet.get_all_records()
        existing_ids = set(str(row.get('Email ID', '')).lower() for row in existing_data)

        if target_id:
            print(f"Processing target ID: {target_id}")
            process_single_message(gmail_service, sheet, target_id, existing_ids)
            return

        # Pagination loop for broader search
        # Refined query to specifically target feedback/communication emails
        query = 'from:feedback@service.alibaba.com'
        print(f"Searching Gmail with query: {query}")
        
        page_token = None
        processed_count = 0
        
        while True:
            list_params = {
                'userId': 'me',
                'q': query,
                'maxResults': MAX_RESULTS_PER_PAGE,
            }
            if page_token:
                list_params['pageToken'] = page_token
                
            results = gmail_service.users().messages().list(**list_params).execute()
            messages = results.get('messages', [])
            
            if not messages:
                print("No matching messages found.")
                break
                
            print(f"Found {len(messages)} messages on this page.")
            for msg in messages:
                if process_single_message(gmail_service, sheet, msg['id'], existing_ids):
                    processed_count += 1
                    if processed_count >= MAX_EMAILS_PER_RUN:
                        print(f"Reached batch limit of {MAX_EMAILS_PER_RUN}. Stopping.")
                        return
                        
                    print(f"Waiting {GEMINI_RETRY_DELAY}s for rate limit...")
                    time.sleep(GEMINI_RETRY_DELAY) # Rate limit delay for Gemini free tier
                    
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
        print(f"\nCompleted! Processed {processed_count} new emails.")
        
    except Exception as e:
        print(f"Fatal Error: {e}")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gmail Sync for Alibaba Agent')
    parser.add_argument('--id', help='Specific Gmail Message ID to process')
    args = parser.parse_args()

    print(f"--- Alibaba Sync Started at {datetime.now().strftime('%H:%M:%S')} ---")
    try:
        fetch_and_process_emails(target_id=args.id)
    except Exception as e:
        print(f"\nTermination due to error: {e}")
        sys.exit(1)
    print("--- Alibaba Sync Finished ---")
