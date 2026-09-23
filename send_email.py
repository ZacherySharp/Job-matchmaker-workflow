"""
Sends a job match notification email via Gmail API (OAuth2).
Attaches tailored PDF resumes and includes a formatted HTML summary.

First-time setup: run this script once standalone — it will open a browser
window to authorize your Google account and save token.json automatically.
"""

import base64
import json
import os
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

ROOT = Path(__file__).parent.parent
TMP_DIR = ROOT / ".tmp"
RANKED_FILE = TMP_DIR / "jobs_ranked.json"
TAILORED_DIR = TMP_DIR / "tailored"

CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

RECIPIENT = os.getenv("GMAIL_ADDRESS", "saqivwilliams45@gmail.com")


def get_gmail_service():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_FILE}\n"
                    "Follow the setup steps in workflows/job_matching_workflow.md "
                    "to download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            print("\n" + "="*60)
            print("GMAIL AUTHORIZATION REQUIRED")
            print("="*60)
            creds = flow.run_local_server(port=8080, open_browser=False)
            print("="*60 + "\n")

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"Authorization saved to {TOKEN_FILE}")

    return build("gmail", "v1", credentials=creds)


def build_html_body(jobs: list[dict]) -> str:
    today = date.today().strftime("%B %d, %Y")
    job_cards = ""
    for i, job in enumerate(jobs, 1):
        score = job.get("match_score", "N/A")
        score_color = "#27ae60" if score >= 70 else "#f39c12" if score >= 50 else "#e74c3c"
        url = job.get("url", "#")
        job_cards += f"""
        <div style="background:#f9f9f9;border-left:4px solid {score_color};padding:16px;margin-bottom:16px;border-radius:4px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <h3 style="margin:0 0 4px 0;color:#1a1a2e;font-size:15px;">{i}. {job.get('title', 'Unknown Role')}</h3>
              <p style="margin:0 0 4px 0;color:#555;font-size:13px;">
                <strong>{job.get('company', '')}</strong> &nbsp;&bull;&nbsp; {job.get('location', '')}
              </p>
            </div>
            <div style="background:{score_color};color:white;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:bold;white-space:nowrap;">
              {score}/100
            </div>
          </div>
          <p style="margin:8px 0 8px 0;color:#333;font-size:13px;font-style:italic;">{job.get('match_reason', '')}</p>
          <a href="{url}" style="color:#0f3460;font-size:12px;text-decoration:none;">View Job Posting &rarr;</a>
        </div>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;padding:20px;color:#333;">
  <div style="background:#1a1a2e;padding:20px 24px;border-radius:8px 8px 0 0;">
    <h1 style="color:white;margin:0;font-size:20px;">Job Matches for {today}</h1>
    <p style="color:#aaa;margin:6px 0 0 0;font-size:13px;">Your top {len(jobs)} opportunities in Kingston + Remote</p>
  </div>
  <div style="border:1px solid #e0e0e0;border-top:none;padding:20px;border-radius:0 0 8px 8px;">
    <p style="font-size:13px;color:#555;">Hi Saqiv, here are your best job matches today. Each attached PDF is a resume tailored specifically for that role. Good luck!</p>
    {job_cards}
    <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
    <p style="font-size:11px;color:#999;">
      Tailored resumes are attached as PDFs &mdash; one per job.<br>
      Powered by the WAT Framework + Claude AI.
    </p>
  </div>
</body>
</html>"""


def send_notification(jobs: list[dict], pdf_paths: list[Path]) -> bool:
    service = get_gmail_service()

    today = date.today().strftime("%b %d, %Y")
    subject = f"Job Matches -- {today} | {len(jobs)} Opportunities Found"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = RECIPIENT
    msg["To"] = RECIPIENT

    msg.attach(MIMEText(build_html_body(jobs), "html"))

    attached = 0
    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            continue
        with open(pdf_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{pdf_path.name}"')
        msg.attach(part)
        attached += 1

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"Email sent to {RECIPIENT} with {attached} PDF attachment(s).")
    return True


def main():
    if not RANKED_FILE.exists():
        print(f"Error: {RANKED_FILE} not found. Run the full workflow first.")
        return False

    with open(RANKED_FILE, encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        print("No ranked jobs -- skipping email.")
        return False

    pdf_paths = sorted(TAILORED_DIR.glob("*.pdf"))
    if not pdf_paths:
        print(f"No PDFs found in {TAILORED_DIR} -- skipping email.")
        return False

    return send_notification(jobs, pdf_paths)


if __name__ == "__main__":
    main()
