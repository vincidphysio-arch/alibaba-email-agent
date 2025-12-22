#!/usr/bin/env python3
"""
Simple one-command script to run tomorrow when API quota resets.
Clears the sheet and syncs your last 10 emails with accurate vendor extraction.
"""
import subprocess
import sys

print("\n🔄 Starting clean sync of last 10 emails...\n")

# Step 1: Clear sheet
print("[1/2] Clearing Google Sheet...")
subprocess.run([sys.executable, "gmail_sync.py", "--clear"], check=True)

# Step 2: Sync last 10
print("[2/2] Syncing last 10 emails...")
subprocess.run([sys.executable, "backfill_data.py"], check=True)

print("\n✅ Done! Check your sheet:")
print("https://docs.google.com/spreadsheets/d/1kSWyTwYxiNYMG6IN_2GWcN4EBsVsTEmm1m_RTuIQ62o/edit\n")
