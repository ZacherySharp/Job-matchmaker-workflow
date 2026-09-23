"""
Uses Claude to tailor resume content for each ranked job.
Reads the appropriate base resume, rewrites it for the job, saves JSON to .tmp/tailored/.
"""

import json
import os
import re
from pathlib import Path

import anthropic
import pdfplumber
from docx import Document
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent.parent
TMP_DIR = ROOT / ".tmp"
RANKED_FILE = TMP_DIR / "jobs_ranked.json"
TAILORED_DIR = TMP_DIR / "tailored"
TAILORED_DIR.mkdir(exist_ok=True)
RESUMES_DIR = ROOT / "resumes"


def extract_resume_text(filename: str) -> str:
    path = RESUMES_DIR / filename
    if not path.exists():
        # Fallback to new resume
        path = RESUMES_DIR / "Saqiv Williams resume new.pdf"

    if path.suffix.lower() == ".pdf":
        try:
            with pdfplumber.open(path) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as e:
            print(f"  Warning: could not read PDF {path.name}: {e}")
            return ""

    if path.suffix.lower() == ".docx":
        try:
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            print(f"  Warning: could not read DOCX {path.name}: {e}")
            return ""

    return ""


def tailor_for_job(client: anthropic.Anthropic, job: dict, base_text: str) -> dict | None:
    prompt = f"""You are a professional resume writer. Tailor the candidate's resume specifically for this job.

JOB DETAILS:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Description:
{job.get('description', '')[:3000]}

BASE RESUME TEXT:
{base_text[:3000]}

Return ONLY valid JSON with this exact structure (no extra text, no markdown fences):
{{
  "name": "Saqiv Williams",
  "phone": "1 (613) 328-1543",
  "email": "saqivwilliams45@gmail.com",
  "linkedin": "linkedin.com/in/saqiv-williams-6aa225384",
  "location": "Kingston, Ontario, Canada",
  "summary": "<2-3 sentence professional summary tailored to this specific role and company>",
  "education": [
    {{
      "institution": "<institution name>",
      "degree": "<degree or qualification>",
      "dates": "<date range>",
      "details": ["<relevant course or achievement>"]
    }}
  ],
  "experience": [
    {{
      "title": "<job title>",
      "organization": "<organization name>",
      "dates": "<date range>",
      "bullets": ["<achievement bullet, reworded to emphasize skills relevant to the target job>"]
    }}
  ],
  "skills": {{
    "technical": ["<skill 1>", "<skill 2>"],
    "soft": ["<skill 1>", "<skill 2>"]
  }},
  "certifications": ["<cert 1>", "<cert 2>"],
  "achievements": ["<achievement 1>", "<achievement 2>"]
}}

Rules:
- Only include true information from the base resume — never fabricate experience
- Reorder bullets and sections to lead with what's most relevant to this job
- Mirror keywords from the job description naturally (for ATS systems)
- Keep bullet points concise and achievement-focused (start with action verbs)
- Summary must mention the company name or role type specifically"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except Exception as e:
        print(f"  Tailoring failed: {e}")
        return None


def make_job_id(job: dict) -> str:
    title = re.sub(r"[^\w]", "_", job.get("title", "job"))[:30]
    company = re.sub(r"[^\w]", "_", job.get("company", "co"))[:20]
    return f"{title}_{company}"


def main():
    if not RANKED_FILE.exists():
        print(f"Error: {RANKED_FILE} not found. Run match_and_rank.py first.")
        return []

    with open(RANKED_FILE, encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        print("No ranked jobs to tailor.")
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env")
        return []

    client = anthropic.Anthropic(api_key=api_key)

    results = []
    print(f"Tailoring resumes for {len(jobs)} jobs...")

    for i, job in enumerate(jobs, 1):
        base_resume = job.get("best_base_resume", "Saqiv Williams resume new.pdf")
        print(f"  [{i}/{len(jobs)}] {job.get('title')} @ {job.get('company')} (base: {base_resume})")

        base_text = extract_resume_text(base_resume)
        if not base_text.strip():
            print(f"    Warning: empty base resume text, skipping.")
            continue

        tailored = tailor_for_job(client, job, base_text)
        if not tailored:
            continue

        job_id = make_job_id(job)
        out_path = TAILORED_DIR / f"{job_id}.json"

        tailored["_job_id"] = job_id
        tailored["_job_title"] = job.get("title", "")
        tailored["_company"] = job.get("company", "")
        tailored["_location"] = job.get("location", "")
        tailored["_url"] = job.get("url", "")
        tailored["_match_score"] = job.get("match_score", 0)
        tailored["_match_reason"] = job.get("match_reason", "")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tailored, f, indent=2)

        print(f"    Saved: {out_path.name}")
        results.append(str(out_path))

    print(f"\nTailored {len(results)} resumes.")
    return results


if __name__ == "__main__":
    main()
