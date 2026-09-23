"""
One-time Gmail OAuth2 authorization.
Prints the authorization URL to auth_url.txt, then waits for you to visit it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"
URL_FILE = ROOT / "auth_url.txt"

flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
flow.redirect_uri = "http://localhost:8080/"
auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

# Write URL to file so it can be read regardless of buffering
URL_FILE.write_text(auth_url)
print(f"Auth URL written to: {URL_FILE}", flush=True)

# Also try printing directly
print("\n" + "="*60, flush=True)
print("OPEN THIS IN YOUR BROWSER:", flush=True)
print(auth_url, flush=True)
print("="*60 + "\n", flush=True)

# Start local server on fixed port to receive the callback
creds = flow.run_local_server(port=8080, open_browser=False)

with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())

print(f"\nSuccess! token.json saved. You can now run the full workflow.", flush=True)
URL_FILE.unlink(missing_ok=True)
