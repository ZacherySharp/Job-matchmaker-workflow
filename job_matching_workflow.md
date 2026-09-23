# Workflow: Automated Job Matching & Resume Tailoring

## Objective
Scrape job boards daily for roles in Kingston, Ontario or remote Canada, score them against Saqiv's profile, tailor a PDF resume for each top match, and send an email notification with all attachments.

## Required Inputs

| Input | Where to set |
|---|---|
| `ANTHROPIC_API_KEY` | `.env` |
| `GMAIL_ADDRESS` | `.env` (pre-set to saqivwilliams45@gmail.com) |
| `credentials.json` | Project root — downloaded from Google Cloud Console (one-time) |
| Resume files | `resumes/` folder (already populated) |

### Gmail OAuth2 Setup (one-time)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (name it anything, e.g. "Job Matcher")
3. In the search bar, search **"Gmail API"** → click it → click **Enable**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
5. Application type: **Desktop app** → click Create
6. Click **Download JSON** → save the file as `credentials.json` in the project root
7. Go to **APIs & Services → OAuth consent screen** → set User type to **External** → add your Gmail as a test user
8. Run `python tools/send_email.py` once — a browser window will open, sign in and click Allow
9. `token.json` is saved automatically. Future runs are fully automatic.

## Running the Workflow

### Manual (one-off run)
```
python tools/run_workflow.py
```

### Scheduled (daily at 8:00 AM)
```
python tools/scheduler.py
```
Keep the terminal open. To change the run time, edit `RUN_TIME = "08:00"` in `tools/scheduler.py`.

### Run a single step
```
python tools/scrape_jobs.py        # Step 1 — fetch jobs
python tools/match_and_rank.py     # Step 2 — score + select top 5
python tools/tailor_resume.py      # Step 3 — rewrite resumes
python tools/generate_pdf.py       # Step 4 — render PDFs
python tools/send_email.py         # Step 5 — send email
```

## Pipeline Steps

```
scrape_jobs → match_and_rank → tailor_resume → generate_pdf → send_email
```

### Step 1 — scrape_jobs.py
- Queries Indeed and LinkedIn using ~15 search terms
- Searches Kingston, Ontario + remote Canada separately
- Deduplicates by URL and title+company pair
- Output: `.tmp/jobs_raw.json`

### Step 2 — match_and_rank.py
- Sends each job to Claude (Haiku) with Saqiv's full profile for scoring
- Filters jobs with match score < 40
- Picks top 5 by score
- For each job, selects the best base resume variant
- Output: `.tmp/jobs_ranked.json`

### Step 3 — tailor_resume.py
- Extracts text from the selected base resume (PDF via pdfplumber, DOCX via python-docx)
- Sends base resume + job description to Claude (Sonnet) for tailoring
- Claude returns structured JSON (summary, education, experience, skills)
- Output: `.tmp/tailored/{job_id}.json` per job

### Step 4 — generate_pdf.py
- Reads each tailored JSON
- Renders a professional PDF using reportlab
- Output: `.tmp/tailored/{job_id}.pdf` per job

### Step 5 — send_email.py
- Builds an HTML email with job cards (title, company, score, reason, apply link)
- Attaches all PDFs
- Sends via Gmail SMTP (port 465, SSL)
- To: saqivwilliams45@gmail.com

## Base Resume Selection

| Job Category | Base Resume Used |
|---|---|
| tech / computing | `Saqiv Williams resume for career fair 2025.pdf` |
| campus / student services | `Saqiv Williams resume RA.pdf` |
| education / tutoring | `Saqiv Williams resume new.pdf` |
| finance / analytics | `Saqiv_Williams_BankOfCanada_v2.docx` |
| general | `Saqiv Williams resume new.pdf` |

Claude classifies each job and selects the appropriate base automatically.

## Edge Cases & Known Constraints

**No jobs found:**
Workflow exits after Step 1 with a log message. This can happen if job boards block the scraper temporarily. Wait a few hours and retry.

**API rate limits:**
- JobSpy may get rate-limited by Indeed or LinkedIn. If this happens repeatedly, reduce the number of search queries in `scrape_jobs.py` or add a `time.sleep(2)` between queries.
- Claude API has per-minute token limits. If scoring 50+ jobs, the script may slow down — this is expected.

**PDF generation errors:**
If a tailored JSON has unexpected structure (missing keys), `generate_pdf.py` will skip that file and print a warning. Check `.tmp/tailored/*.json` for malformed output.

**Gmail App Password:**
- Must be a 16-character App Password, not your regular Gmail password
- 2-Factor Authentication must be enabled on the Google account first
- Generate at: myaccount.google.com → Security → 2-Step Verification → App passwords

**Empty resume text:**
If a base resume can't be read (corrupted file, encoding issue), `tailor_resume.py` skips that job. Verify the file opens normally in a PDF viewer or Word.

## Adjusting Search Behaviour

**Change search queries:** Edit `SEARCH_QUERIES` list in `tools/scrape_jobs.py`

**Change number of top matches:** Edit `TOP_N = 5` in `tools/match_and_rank.py`

**Change run time:** Edit `RUN_TIME = "08:00"` in `tools/scheduler.py`

**Change match score threshold:** Edit the `>= 40` filter in `tools/match_and_rank.py`

## File Structure

```
.tmp/
  jobs_raw.json          # Overwritten every run
  jobs_ranked.json       # Top 5 matches
  tailored/
    {job_id}.json        # Tailored resume data
    {job_id}.pdf         # Final PDF attachment
```

All `.tmp/` files are regenerated on each run and are gitignored.
