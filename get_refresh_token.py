#!/usr/bin/env python3
"""
One-time script to exchange OAuth authorization code for refresh token.
Run this locally after obtaining the authorization code.
"""

import requests
import json

# OAuth credentials - You can set these in your .env or enter them when prompted
import os
from datetime import datetime

# Simple .env loader
def load_env():
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ[key] = val

load_env()

CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID")
CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET")
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

def get_refresh_token(client_id, client_secret, auth_code):
    """Exchange authorization code for refresh token"""
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    
    print(f"\nExchanging code for token for Client: {client_id[:15]}...")
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        refresh_token = tokens.get("refresh_token")
        
        print("\nSUCCESS! Token exchange completed.\n")
        print(f"Access Token: {tokens.get('access_token')[:30]}...")
        
        if refresh_token:
            print("\nREFRESH TOKEN (save this securely):")
            print(f"REFR_TOKEN_START >> {refresh_token} << REFR_TOKEN_END")
            print("\nAdd this to GitHub Actions secrets AND your .env file as: OAUTH_REFRESH_TOKEN")
        else:
            print("\nWARNING: No refresh token returned. This usually happens if 'prompt=consent' or 'access_type=offline' was missing from the auth URL.")
            print("Try generating a new auth code using the URL in OAUTH_SETUP.md.")
            
        return tokens
    else:
        print("\nERROR! Failed to get tokens.")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None

if __name__ == "__main__":
    print("--- Google OAuth Refresh Token Generator ---")
    
    c_id = CLIENT_ID or input("Enter OAUTH_CLIENT_ID: ").strip()
    c_secret = CLIENT_SECRET or input("Enter OAUTH_CLIENT_SECRET: ").strip()
    
    print("\n1. Visit the following URL to get your Authorization Code:")
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={c_id}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/gmail.readonly+https://www.googleapis.com/auth/spreadsheets&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    print(f"\n{auth_url}\n")
    
    a_code = input("2. Enter the Authorization Code from the website: ").strip()
    
    if all([c_id, c_secret, a_code]):
        get_refresh_token(c_id, c_secret, a_code)
    else:
        print("\nError: Missing required information.")
