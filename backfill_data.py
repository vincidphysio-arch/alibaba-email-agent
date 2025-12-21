import time
from gmail_sync import get_gmail_service, get_sheets_service, process_single_message, SHEET_ID

def backfill_all_emails():
    print("--- Alibaba Backfill Tool ---")
    print("Initiating full historical backfill...")
    
    # 1. Connect
    print("Connecting to services...")
    gmail_service = get_gmail_service()
    gc = get_sheets_service()
    sh = gc.open_by_key(SHEET_ID).sheet1
    
    # 2. Clear Sheet
    print("Clearing sheet to ensure fresh start...")
    sh.clear()
    headers = ['Timestamp', 'Email ID', 'Vendor', 'Summary', 'Quality Score', 'Subject', 'From']
    sh.append_row(headers)
    print("Sheet cleared and headers reset.")
    
    # 3. Setup Pagination
    query = 'from:feedback@service.alibaba.com'
    print(f"Fetching ALL emails matching: {query}")
    
    # Wait a bit to ensure we aren't starting in a penalty box
    print("Initializing Overnight Repair Mode...")
    print("Waiting 60s before first request...")
    time.sleep(60)
    
    page_token = None
    total_processed = 0
    existing_ids = set() 
    
    while True:
        try:
            list_params = {
                'userId': 'me',
                'q': query,
                'maxResults': 50 
            }
            if page_token:
                list_params['pageToken'] = page_token
                
            results = gmail_service.users().messages().list(**list_params).execute()
            messages = results.get('messages', [])
            
            if not messages:
                print("No more messages found.")
                break
                
            print(f"Found {len(messages)} messages on current page. Processing...")
            
            for msg in messages:
                msg_id = msg['id']
                print(f"Processing {total_processed + 1}: {msg_id}")
                
                # Infinite retry loop for the single message processing
                while True:
                    try:
                        success = process_single_message(gmail_service, sh, msg_id, existing_ids)
                        if success:
                            total_processed += 1
                            # ULTRA SAFE: 30 seconds = 2 RPM. 
                            # This takes ~7 hours for 800 emails, but guarantees execution.
                            print("Sleeping 30s (Overnight Mode)...")
                            time.sleep(30)
                        else:
                            time.sleep(2)
                        break # Break retry loop on success or skip

                    except Exception as e:
                        if "429" in str(e) or "Quota exceeded" in str(e):
                            print(f"HIT RATE LIMIT: {e}")
                            print("Sleeping 10 MINUTES to let quota reset...")
                            time.sleep(600) # 10 minute cooling off
                            continue # Retry the same message
                        else:
                            print(f"Unknown error: {e}. Skipping message.")
                            break
            
            page_token = results.get('nextPageToken')
            if not page_token:
                print("End of pagination reached.")
                break
                
        except Exception as e:
            print(f"Error during pagination: {e}")
            print("Waiting 5 minutes...")
            time.sleep(300)
            
    print(f"Backfill Complete! Total processed: {total_processed}")

if __name__ == "__main__":
    backfill_all_emails()
