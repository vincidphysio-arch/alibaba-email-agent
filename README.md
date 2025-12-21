# Alibaba Email Agent

**AI-powered email monitoring system for Alibaba vendor quotes.**

This agent automatically:
1.  Checks Gmail for messages from `feedback@service.alibaba.com`.
2.  Uses **Google Gemini AI** to extract the *real* vendor name and summarize the conversation.
3.  Saves the data to a Google Sheet.
4.  Displays insights on a Streamlit Dashboard.

## 🚀 Setup Guide

### 1. GitHub Actions (Automated Sync)
For the minute-by-minute sync to work on GitHub, you must set the following **Secrets** in your Repository Settings:

1.  Go to **Settings** > **Secrets and variables** > **Actions**.
2.  Click **New repository secret**.
3.  Add the following secrets (copy values from your local `.env` file):

| Secret Name | Description |
| :--- | :--- |
| `GEMINI_API_KEY` | Your Google Gemini API Key. |
| `OAUTH_CLIENT_ID` | Google Cloud OAuth Client ID. |
| `OAUTH_CLIENT_SECRET` | Google Cloud OAuth Client Secret. |
| `OAUTH_REFRESH_TOKEN` | The Refresh Token generated during setup. |
| `SHEET_ID` | The ID of your Google Sheet (from the URL). |

> **Note:** The workflow will fail ("Run failed") until these secrets are added. This is normal because the cloud runner cannot see your local files for security reasons.

### 2. Local Usage
To run the agent locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the sync manually
python gmail_sync.py

# Run the dashboard
streamlit run app.py
```

### 3. File Structure
*   `gmail_sync.py`: Main logic. Fetches emails, matches patterns, calls Gemini, writes to Sheets.
*   `.github/workflows/sync-emails.yml`: Configuration for the automatic minute-by-minute cloud schedule.
*   `app.py`: The Streamlit dashboard.
*   `backfill_data.py`: Specialized script for historical data repair (slow & safe).
