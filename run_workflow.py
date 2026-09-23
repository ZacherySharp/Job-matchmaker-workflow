"""
Orchestrator: runs the full job matching pipeline end-to-end.

Steps:
  1. scrape_jobs       — fetch fresh job listings
  2. match_and_rank    — score + pick top 5
  3. tailor_resume     — rewrite resume for each job
  4. generate_pdf      — render PDFs
  5. send_email        — notify via Gmail

Usage:
  python tools/run_workflow.py
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import generate_pdf
import match_and_rank
import scrape_jobs
import send_email
import tailor_resume


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def clean_tmp():
    tailored_dir = ROOT / ".tmp" / "tailored"
    tailored_dir.mkdir(parents=True, exist_ok=True)
    for f in tailored_dir.glob("*"):
        f.unlink()


def run():
    start = datetime.now()
    log("=== Job Matching Workflow Started ===")

    # Step 1: Scrape
    log("Step 1/5 — Scraping job boards...")
    try:
        jobs_raw = scrape_jobs.main()
        log(f"         Found {len(jobs_raw)} unique job listings.")
    except Exception:
        log("FAILED at scrape_jobs:")
        traceback.print_exc()
        return False

    if not jobs_raw:
        log("No jobs found. Ending workflow.")
        return False

    # Step 2: Match and rank
    log("Step 2/5 — Scoring and ranking jobs...")
    try:
        ranked = match_and_rank.main()
        log(f"         Top {len(ranked)} matches selected.")
    except Exception:
        log("FAILED at match_and_rank:")
        traceback.print_exc()
        return False

    if not ranked:
        log("No qualifying matches found. Ending workflow.")
        return False

    # Step 3: Tailor resumes
    log("Step 3/5 — Tailoring resumes...")
    clean_tmp()
    try:
        tailored_files = tailor_resume.main()
        log(f"         {len(tailored_files)} resumes tailored.")
    except Exception:
        log("FAILED at tailor_resume:")
        traceback.print_exc()
        return False

    # Step 4: Generate PDFs
    log("Step 4/5 — Generating PDFs...")
    try:
        pdfs = generate_pdf.main()
        log(f"         {len(pdfs)} PDFs generated.")
    except Exception:
        log("FAILED at generate_pdf:")
        traceback.print_exc()
        return False

    # Step 5: Send email
    log("Step 5/5 — Sending email notification...")
    try:
        success = send_email.main()
        if success:
            log("         Email delivered successfully.")
        else:
            log("         Email sending skipped or failed (check .env).")
    except Exception:
        log("FAILED at send_email:")
        traceback.print_exc()

    elapsed = (datetime.now() - start).seconds
    log(f"=== Workflow complete in {elapsed}s ===")
    return True


if __name__ == "__main__":
    run()
