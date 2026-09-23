"""
Runs the job matching workflow daily at 8:00 AM.
Keep this script running in a terminal (or register it in Windows Task Scheduler).

Usage:
  python tools/scheduler.py
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import schedule

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import run_workflow

RUN_TIME = "08:00"


def job():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Scheduled run triggered.")
    run_workflow.run()


def main():
    print(f"Scheduler started. Workflow will run daily at {RUN_TIME}.")
    print("Press Ctrl+C to stop.\n")

    schedule.every().day.at(RUN_TIME).do(job)

    # Show next run time
    next_run = schedule.next_run()
    print(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
