"""
Scores each scraped job against Saqiv's profile using Claude API.
Selects top 5 matches and chooses the best base resume for each.
Outputs .tmp/jobs_ranked.json.
"""

import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
TMP_DIR = ROOT / ".tmp"
INPUT_FILE = TMP_DIR / "jobs_raw.json"
OUTPUT_FILE = TMP_DIR / "jobs_ranked.json"
RESUMES_DIR = ROOT / "resumes"

TOP_N = 5

# Saqiv's profile — used as context for every scoring call
CANDIDATE_PROFILE = """
NAME: Saqiv Williams
LOCATION: Kingston, Ontario, Canada (also eligible for remote roles in Canada)
UNIVERSITY: Queen's University, School of Computing — Bachelor of Computing, double major Computing + Economics (2025–present)
PRIOR EDUCATION: CAPE Computer Science (I & II), Information Technology (I & II), Chemistry; CSEC distinctions in Math, IT, English, Chemistry, Physics, Biology, Spanish
CERTIFICATIONS: Harvard CS50 (in progress), Google Data Analytics Certificate (in progress), UWI Web Development

WORK EXPERIENCE:
- Head Chess Coach, Queen's University (current): curriculum design, session planning, Canadian University Chess Championships coordination
- Founder & IT Tutor (2024–present): one-on-one and group IT/programming tutoring, 100% pass rate, 70%+ students achieving grade B+
- IT Teacher, Hillview College, T&T (2024–2025): taught 100+ students core IT and programming, hardware management
- Chess Coach & Volunteer Mentor (ongoing): youth development, tournament prep, community programs

TECHNICAL SKILLS: Python, HTML, CSS, JavaScript, data analysis, Microsoft Office, Google Workspace
SOFT SKILLS: leadership, mentorship, public speaking, curriculum development, program coordination, administrative organization, customer service, bilingual (English, Spanish, conversational French)
ACHIEVEMENTS: Top 3 under-18 tennis T&T, 8 local titles; Top 10 under-20 chess; Queen's Intramural Pickleball Champion; Senior Prefect

RESUME VARIANTS AVAILABLE:
- tech/computing roles: "Saqiv Williams resume for career fair 2025.pdf"
- campus/residence roles (RA, RPA, RFA): "Saqiv Williams resume RA.pdf" or "Saqiv Williams resume RPA.pdf"
- education/tutoring roles: "Saqiv Williams resume new.pdf"
- finance/analytics roles: "Saqiv_Williams_BankOfCanada_v2.docx"
- general: "Saqiv Williams resume new.pdf"
"""

BASE_RESUME_MAP = {
    "tech": "Saqiv Williams resume for career fair 2025.pdf",
    "campus": "Saqiv Williams resume RA.pdf",
    "education": "Saqiv Williams resume new.pdf",
    "finance": "Saqiv_Williams_BankOfCanada_v2.docx",
    "general": "Saqiv Williams resume new.pdf",
}


BATCH_SIZE = 8  # Jobs scored per API call


def score_batch(client: anthropic.Anthropic, jobs: list[dict]) -> list[dict | None]:
    jobs_text = ""
    for i, job in enumerate(jobs):
        jobs_text += f"""
JOB {i + 1}:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Description: {job.get('description', '')[:800]}
---"""

    prompt = f"""You are evaluating job fit for a candidate. Return ONLY a valid JSON array with no extra text.

CANDIDATE PROFILE:
{CANDIDATE_PROFILE}

JOBS TO EVALUATE:
{jobs_text}

Return a JSON array with exactly {len(jobs)} objects, one per job in order:
[
  {{
    "match_score": <integer 0-100>,
    "match_reason": "<1-2 sentences explaining fit>",
    "job_category": "<one of: tech, campus, education, finance, general>",
    "best_base_resume": "<filename from the RESUME VARIANTS AVAILABLE list above>"
  }},
  ...
]

Score 0-100 where:
- 70+: Strong match (experience clearly transferable)
- 50-69: Moderate match (candidate could stretch)
- Below 50: Weak match

Only score highly jobs Saqiv is genuinely qualified for as a first-year university student."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        results = json.loads(text)
        if isinstance(results, list) and len(results) == len(jobs):
            return results
        return [None] * len(jobs)
    except Exception as e:
        print(f"    Batch scoring failed: {e}")
        return [None] * len(jobs)


def main():
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Run scrape_jobs.py first.")
        return []

    with open(INPUT_FILE, encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        print("No jobs to rank.")
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env")
        return []

    client = anthropic.Anthropic(api_key=api_key)

    num_batches = (len(jobs) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Scoring {len(jobs)} jobs in {num_batches} batches of up to {BATCH_SIZE}...")
    scored = []
    for batch_num in range(num_batches):
        start = batch_num * BATCH_SIZE
        batch = jobs[start: start + BATCH_SIZE]
        print(f"  Batch [{batch_num + 1}/{num_batches}] — scoring {len(batch)} jobs...")
        results = score_batch(client, batch)
        for job, result in zip(batch, results):
            if result and result.get("match_score", 0) >= 40:
                job["match_score"] = result["match_score"]
                job["match_reason"] = result["match_reason"]
                job["job_category"] = result.get("job_category", "general")
                job["best_base_resume"] = result.get(
                    "best_base_resume",
                    BASE_RESUME_MAP.get(result.get("job_category", "general"), "Saqiv Williams resume new.pdf")
                )
                scored.append(job)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    top = scored[:TOP_N]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(top, f, indent=2, default=str)

    print(f"\nTop {len(top)} matches saved to {OUTPUT_FILE}")
    for job in top:
        print(f"  [{job['match_score']}] {job['title']} @ {job['company']} — {job['match_reason'][:80]}")

    return top


if __name__ == "__main__":
    main()
