import os
from gmail_sync import get_sheets_service, SHEET_ID, load_env_file

load_env_file()

def force_clear():
    print(f"Connecting to Sheet: {SHEET_ID}")
    gc = get_sheets_service()
    sh = gc.open_by_key(SHEET_ID).sheet1
    
    # Clear all content
    print("Force clearing all rows...")
    sh.clear()
    
    # Reset headers
    headers = ['Timestamp', 'Email ID', 'Vendor', 'Summary', 'Quality Score', 'Subject', 'From']
    sh.append_row(headers)
    print("SUCCESS: Sheet is now 100% clean with fresh headers.")

if __name__ == "__main__":
    force_clear()
