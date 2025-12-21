import os

# Simple .env loader
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

with open('debug_env.txt', 'w') as f:
    f.write(f"SHEET_ID: {os.environ.get('SHEET_ID')}\n")
    f.write(f"OAUTH_CLIENT_ID: {os.environ.get('OAUTH_CLIENT_ID')}\n")
    f.write(f"OAUTH_CLIENT_SECRET: {os.environ.get('OAUTH_CLIENT_SECRET')}\n")
    f.write(f"OAUTH_REFRESH_TOKEN: {os.environ.get('OAUTH_REFRESH_TOKEN')}\n")
    f.write(f"GEMINI_API_KEY: {os.environ.get('GEMINI_API_KEY')}\n")
