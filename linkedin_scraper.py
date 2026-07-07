"""
LinkedIn Job Scraper (No Login Required)
=========================================
Uses LinkedIn's public guest API — no browser, no login needed.
Faster and more reliable than Selenium/Playwright approaches.

Usage:
    python linkedin_scraper.py --location "United States" --time 24h --work-type remote
    python linkedin_scraper.py --location "Europe" --time week --work-type full-time
    python linkedin_scraper.py --location "Italy" --time month --work-type any --keywords "data scientist"
"""

import argparse
import csv
import json
import sys
import time
import random
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ─── LinkedIn guest API endpoints (no login required) ─────────────────────────
SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.linkedin.com/jobs/search/",
}

# ─── Filter mappings ──────────────────────────────────────────────────────────
TIME_FILTERS = {
    "24h":   "r86400",
    "week":  "r604800",
    "month": "r2592000",
    "any":   "",
}

WORK_TYPE_FILTERS = {
    "full-time":  "F",
    "part-time":  "P",
    "remote":     "2",
    "contract":   "C",
    "internship": "I",
    "any":        "",
}

# ─── Search: get job IDs ──────────────────────────────────────────────────────

def search_jobs(keywords, location, time_filter, work_type, max_jobs=50):
    """Fetch job IDs from LinkedIn's guest search API."""
    job_ids = []
    start = 0
    batch = 25  # LinkedIn returns 25 per page

    print(f"🔍 Searching LinkedIn for '{keywords}' in '{location}'...")

    while len(job_ids) < max_jobs:
        params = {
            "keywords": keywords,
            "location": location,
            "start":    start,
        }
        if time_filter != "any":
            params["f_TPR"] = TIME_FILTERS[time_filter]
        if work_type != "any":
            params["f_JT"] = WORK_TYPE_FILTERS[work_type]

        try:
            resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"   ⚠️  Search returned {resp.status_code}, stopping.")
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("li")

            if not cards:
                break  # no more results

            for card in cards:
                entity = card.find("div", {"data-entity-urn": True})
                if entity:
                    urn = entity["data-entity-urn"]  # e.g. "urn:li:jobPosting:123456789"
                    job_id = urn.split(":")[-1]
                    job_ids.append(job_id)

            print(f"   Found {len(job_ids)} jobs so far...", end="\r")
            start += batch

            # Polite delay between pages
            time.sleep(random.uniform(1.0, 2.0))

        except requests.RequestException as e:
            print(f"\n   ⚠️  Network error: {e}")
            break

    print(f"\n✅ Found {len(job_ids)} job IDs")
    return job_ids[:max_jobs]


# ─── Detail: get full job info ────────────────────────────────────────────────

def get_job_detail(job_id, location, work_type):
    """Fetch full details for a single job from LinkedIn's guest detail API."""
    url = DETAIL_URL.format(job_id=job_id)
    job_link = f"https://www.linkedin.com/jobs/view/{job_id}/"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Job title
        title_el = soup.find("h2", {"class": lambda c: c and "top-card-layout__title" in c})
        title = title_el.get_text(strip=True) if title_el else ""

        # Company name
        company_el = soup.find("a", {"class": lambda c: c and "topcard__org-name-link" in c})
        if not company_el:
            company_el = soup.find("span", {"class": lambda c: c and "topcard__flavor" in c})
        company = company_el.get_text(strip=True) if company_el else ""

        # Description
        desc_el = soup.find("div", {"class": lambda c: c and "description__text" in c})
        description = desc_el.get_text(separator=" ", strip=True) if desc_el else ""
        description = " ".join(description.split())  # normalize whitespace

        # Salary
        salary = ""
        salary_el = soup.find("div", {"class": lambda c: c and "compensation" in (c or "")})
        if not salary_el:
            # Try salary inside criteria
            for li in soup.find_all("li", {"class": lambda c: c and "description__job-criteria-item" in (c or "")}):
                label = li.find("h3")
                value = li.find("span")
                if label and value:
                    label_text = label.get_text(strip=True).lower()
                    if "salary" in label_text or "compensation" in label_text:
                        salary = value.get_text(strip=True)
                        break
        else:
            salary = salary_el.get_text(strip=True)

        # Experience level & job type from criteria list
        experience_level = ""
        job_type_detail  = ""
        for li in soup.find_all("li", {"class": lambda c: c and "description__job-criteria-item" in (c or "")}):
            label = li.find("h3")
            value = li.find("span")
            if label and value:
                label_text = label.get_text(strip=True).lower()
                value_text = value.get_text(strip=True)
                if "seniority" in label_text or "experience" in label_text:
                    experience_level = value_text
                elif "employment" in label_text or "job type" in label_text:
                    job_type_detail = value_text

        return {
            "job_link":         job_link,
            "job_title":        title,
            "company_name":     company,
            "description":      description[:3000] + "..." if len(description) > 3000 else description,
            "salary":           salary or "Not specified",
            "experience_level": experience_level or "Not specified",
            "job_type":         job_type_detail or work_type.title(),
            "location":         location,
            "scraped_at":       datetime.now().isoformat(),
        }

    except requests.RequestException:
        return None


# ─── Save output ──────────────────────────────────────────────────────────────

def save_results(jobs, output_prefix):
    """Save results to CSV and JSON."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"{output_prefix}_{timestamp}.json"
    csv_file  = f"{output_prefix}_{timestamp}.csv"

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    if jobs:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
            writer.writeheader()
            writer.writerows(jobs)

    print(f"\n✅ Saved {len(jobs)} jobs:")
    print(f"   📄 JSON : {json_file}")
    print(f"   📊 CSV  : {csv_file}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="LinkedIn Job Scraper — no login required",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python linkedin_scraper.py --location "United States" --time 24h --work-type remote
  python linkedin_scraper.py --location "Europe" --time week --work-type full-time --keywords "data scientist"
  python linkedin_scraper.py --location "Italy" --time month --work-type any --max-jobs 100
        """,
    )
    parser.add_argument("--location",  required=True, help='Location (e.g. "United States", "Europe", "Remote")')
    parser.add_argument("--time",      required=True, choices=["24h", "week", "month", "any"])
    parser.add_argument("--work-type", required=True, choices=["full-time", "part-time", "remote", "contract", "internship", "any"])
    parser.add_argument("--keywords",  default="software engineer", help='Search keywords (default: "software engineer")')
    parser.add_argument("--max-jobs",  type=int, default=50, help="Max jobs to scrape (default: 50)")
    parser.add_argument("--output",    default="linkedin_jobs", help="Output filename prefix")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 55)
    print("       LinkedIn Job Scraper (No Login)")
    print("=" * 55)
    print(f"  Location  : {args.location}")
    print(f"  Time      : {args.time}")
    print(f"  Work Type : {args.work_type}")
    print(f"  Keywords  : {args.keywords}")
    print(f"  Max Jobs  : {args.max_jobs}")
    print("=" * 55 + "\n")

    # Step 1: get job IDs from search
    job_ids = search_jobs(
        keywords=args.keywords,
        location=args.location,
        time_filter=args.time,
        work_type=args.work_type,
        max_jobs=args.max_jobs,
    )

    if not job_ids:
        print("❌ No jobs found. Try different filters or keywords.")
        sys.exit(1)

    # Step 2: get full details for each job
    print(f"\n📋 Fetching details for {len(job_ids)} jobs...\n")
    jobs = []
    for idx, job_id in enumerate(job_ids):
        print(f"   [{idx+1}/{len(job_ids)}] Job ID: {job_id}", end="\r")
        detail = get_job_detail(job_id, args.location, args.work_type)
        if detail:
            jobs.append(detail)
        # Polite delay to avoid rate limiting
        time.sleep(random.uniform(0.8, 1.5))

    print(f"\n✅ Successfully scraped {len(jobs)} jobs!\n")

    # Step 3: save
    save_results(jobs, args.output)

    # Step 4: print sample
    if jobs:
        print("\n📋 Sample (first result):")
        print("-" * 45)
        s = jobs[0]
        for k, v in s.items():
            if k != "description":
                print(f"  {k:20}: {v}")
        print(f"  {'description':20}: {s['description'][:120]}...")


if __name__ == "__main__":
    main()
