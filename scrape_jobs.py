"""
Scrapes Indeed and LinkedIn for jobs in Kingston, Ontario or remote (Canada).
Outputs .tmp/jobs_raw.json with deduplicated job listings.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from jobspy import scrape_jobs

load_dotenv()

ROOT = Path(__file__).parent.parent
TMP_DIR = ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = TMP_DIR / "jobs_raw.json"

SEARCH_QUERIES = [
    # Tech / Computing
    "software developer",
    "data analyst",
    "junior developer",
    "computing internship",
    "web developer",
    # Campus / Student Services
    "residence assistant",
    "student services",
    "residence program assistant",
    "campus coordinator",
    # Education / Tutoring
    "tutor",
    "teaching assistant",
    "education coordinator",
    # Finance / Analytics
    "financial analyst",
    "business analyst",
    "investment analyst",
    # General entry-level
    "entry level part time student",
]

SITES = ["indeed", "linkedin"]
DAYS_OLD = 14


def scrape_location(query: str, location: str, is_remote: bool) -> list[dict]:
    try:
        df = scrape_jobs(
            site_name=SITES,
            search_term=query,
            location=location,
            results_wanted=10,
            hours_old=DAYS_OLD * 24,
            country_indeed="Canada",
            is_remote=is_remote,
            verbose=0,
        )
        if df is None or df.empty:
            return []
        jobs = []
        for _, row in df.iterrows():
            jobs.append({
                "id": str(row.get("id", "")),
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "location": str(row.get("location", "")),
                "description": str(row.get("description", ""))[:4000],
                "url": str(row.get("job_url", "")),
                "date_posted": str(row.get("date_posted", "")),
                "site": str(row.get("site", "")),
                "is_remote": bool(row.get("is_remote", is_remote)),
                "query": query,
            })
        return jobs
    except Exception as e:
        print(f"  Warning: query='{query}' location='{location}' failed: {e}")
        return []


def deduplicate(jobs: list[dict]) -> list[dict]:
    seen_urls = set()
    seen_titles = {}
    unique = []
    for job in jobs:
        url = job.get("url", "")
        key = f"{job.get('title','').lower().strip()}|{job.get('company','').lower().strip()}"
        if url and url in seen_urls:
            continue
        if key in seen_titles:
            continue
        if url:
            seen_urls.add(url)
        seen_titles[key] = True
        unique.append(job)
    return unique


def main():
    all_jobs = []
    total_queries = len(SEARCH_QUERIES)

    print(f"Scraping {total_queries} search queries across {len(SITES)} sites...")

    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"  [{i}/{total_queries}] '{query}'")

        # Kingston, ON in-person roles
        kingston_jobs = scrape_location(query, "Kingston, Ontario, Canada", is_remote=False)
        all_jobs.extend(kingston_jobs)

        # Remote Canada roles
        remote_jobs = scrape_location(query, "Canada", is_remote=True)
        all_jobs.extend(remote_jobs)

    unique_jobs = deduplicate(all_jobs)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, indent=2, default=str)

    print(f"\nDone. {len(all_jobs)} total -> {len(unique_jobs)} unique jobs saved to {OUTPUT_FILE}")
    return unique_jobs


if __name__ == "__main__":
    main()
