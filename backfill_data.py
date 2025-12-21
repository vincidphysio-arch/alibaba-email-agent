import time
from gmail_sync import get_gmail_service, get_sheets_service, process_single_message, SHEET_ID

def backfill_limited():
    print("--- Alibaba Targeted Sync (Last 10) ---")
    
    # 1. Connect
    print("Connecting to services...")
    gmail_service = get_gmail_service()
    gc = get_sheets_service()
    sh = gc.open_by_key(SHEET_ID).sheet1
    
    # 2. Fetch ONLY LAST 10 emails
    query = 'from:feedback@service.alibaba.com'
    print(f"Fetching LAST 10 emails matching: {query}")
    results = gmail_service.users().messages().list(userId='me', q=query, maxResults=10).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print("No messages found.")
        return

    print(f"Starting analysis of {len(messages)} recent emails...")
    total_processed = 0
    existing_ids = set()

    for msg in messages:
        msg_id = msg['id']
        print(f"\n--- Processing Profile {total_processed + 1}/{len(messages)}: {msg_id} ---")
        
        while True:
            try:
                success = process_single_message(gmail_service, sh, msg_id, existing_ids)
                if success:
                    total_processed += 1
                    print("Success! Sleeping 30s to respect API quota...")
                    time.sleep(30)
                break
            except Exception as e:
                if "429" in str(e) or "Quota exceeded" in str(e):
                    print(f"RATE LIMIT hit. Waiting 10 minutes to reset quota...")
                    time.sleep(600)
                    continue 
                else:
                    print(f"Error: {e}. Skipping.")
                    break

    print(f"Targeted Sync Complete! Total processed: {total_processed}")

if __name__ == "__main__":
    backfill_limited()
