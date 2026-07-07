# LinkedIn Job Scraper

Scrapes LinkedIn job listings by location, time filter, and work type.
Outputs clean CSV + JSON files.

## Setup (one time)

```bash
cd d:\devloper\linkedin-scraper

pip install -r requirements.txt

playwright install chromium
```

## Usage

```bash
# Remote jobs in US posted in last 24h
python linkedin_scraper.py --location "United States" --time 24h --work-type remote

# Full-time jobs in Europe this week
python linkedin_scraper.py --location "Europe" --time week --work-type full-time

# Any jobs in Italy this month (with login for more results)
python linkedin_scraper.py --location "Italy" --time month --work-type any --email you@email.com --password yourpass

# Data science jobs, max 100 results
python linkedin_scraper.py --location "Remote" --time any --work-type remote --keywords "data scientist" --max-jobs 100
```

## All Options

| Flag | Required | Description |
|------|----------|-------------|
| --location | ✅ | Country, city, or region |
| --time | ✅ | 24h / week / month / any |
| --work-type | ✅ | full-time / part-time / remote / contract / internship / any |
| --keywords | ❌ | Search keywords (default: "software engineer") |
| --max-jobs | ❌ | Max results (default: 50) |
| --email | ❌ | LinkedIn email (more results with login) |
| --password | ❌ | LinkedIn password |
| --headless | ❌ | Hide browser window |
| --output | ❌ | Output filename prefix |

## Output Files

```
linkedin_jobs_20240315_143022.csv
linkedin_jobs_20240315_143022.json
```

Each record contains:
- job_link
- job_title
- company_name
- description
- salary
- experience_level
- job_type
- location
- scraped_at

## WARNING

LinkedIn's ToS prohibits scraping. Use a secondary account.
For educational/research purposes only.
