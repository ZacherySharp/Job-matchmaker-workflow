"""
Modal deployment for the job matching workflow.
Runs tools/run_workflow.py daily at 8:00 AM Toronto time in Modal's cloud.

One-time setup:
  modal token new
  modal secret create job-matcher-env --from-dotenv .env
  modal secret create job-matcher-gmail GMAIL_TOKEN_JSON="$(cat token.json)"

Deploy:
  modal deploy modal_app.py

Test run (uses Anthropic credits):
  modal run modal_app.py
"""

import os
from pathlib import Path

import modal

APP_DIR = "/root/app"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir("tools", f"{APP_DIR}/tools", ignore=["__pycache__"])
    .add_local_dir("resumes", f"{APP_DIR}/resumes")
)

app = modal.App("job-matcher", image=image)


@app.function(
    secrets=[
        modal.Secret.from_name("job-matcher-env"),
        modal.Secret.from_name("job-matcher-gmail"),
    ],
    schedule=modal.Cron("0 8 * * *", timezone="America/Toronto"),
    timeout=60 * 60,
)
def run_daily():
    import sys

    # send_email.py reads the Gmail OAuth token from token.json in the project root
    token_json = os.environ.get("GMAIL_TOKEN_JSON")
    if token_json:
        Path(APP_DIR, "token.json").write_text(token_json)

    sys.path.insert(0, f"{APP_DIR}/tools")
    import run_workflow

    if not run_workflow.run():
        raise RuntimeError("Workflow did not complete — check the logs above.")


@app.local_entrypoint()
def main():
    run_daily.remote()
