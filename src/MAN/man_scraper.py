"""
Manitoba Government Job Scraper

This scraper:
1. Loads ALL jobs from the Manitoba job search page (no keyword search needed)
2. Token matches all job titles against keywords from list-of-jobs.txt
3. Clicks each matched job to load details (JavaScript scrolls to bottom)
4. Scrapes the full job posting content
5. Saves to JSON + HTML with duplicate detection

Note: The scraper dynamically extracts all jobs from the table, regardless of how many 
there are (72 today, but could be more or less in the future).
"""

import json
import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from playwright.sync_api import sync_playwright, Page, Browser

from .config import (
    BASE_URL,
    SEARCH_URL,
    JOBS_JSON_DIR,
    JOBS_HTML_DIR,
    LOG_DIR,
    JOB_LIST_FILE,
    HEADLESS,
    TIMEOUT,
    DELAY_BETWEEN_JOBS
)
from .models import MANJob
from .parser import parse_job_details

# Set up logging
log_file = LOG_DIR / f"man_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_keywords() -> List[str]:
    """
    Load job keywords from the keywords file.
    
    Returns:
        List of keywords to match against
    """
    try:
        with open(JOB_LIST_FILE, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        logger.info(f"✓ Loaded {len(keywords)} keywords from {JOB_LIST_FILE.name}")
        return keywords
    except Exception as e:
        logger.error(f"✗ Error loading keywords: {e}")
        return []


def token_match_title(job_title: str, keywords: List[str]) -> Tuple[Optional[str], int]:
    """
    Match job title against keywords using token-based matching.
    
    Uses 5-tier scoring system:
    - 100: Exact match (case-insensitive)
    - 95: Exact match of all keyword tokens in job title
    - 90: Keyword is subset of job title tokens
    - 88: Job title is subset of keyword tokens
    - 85: Partial token overlap (50%+)
    
    Args:
        job_title: Job title to match
        keywords: List of keywords to match against
    
    Returns:
        Tuple of (matched_keyword, score) or (None, 0) if no match
    """
    job_title_lower = job_title.lower()
    job_tokens = set(re.findall(r'\b\w+\b', job_title_lower))
    
    best_match = None
    best_score = 0
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        keyword_tokens = set(re.findall(r'\b\w+\b', keyword_lower))
        
        # Skip if no valid tokens
        if not keyword_tokens:
            continue
        
        # Tier 1: Exact match (100)
        if job_title_lower == keyword_lower:
            return (keyword, 100)
        
        # Tier 2: All keyword tokens in job title (95)
        if keyword_tokens.issubset(job_tokens):
            if best_score < 95:
                best_match = keyword
                best_score = 95
        
        # Tier 3: Keyword tokens subset of job title (90)
        elif keyword_tokens.issubset(job_tokens):
            if best_score < 90:
                best_match = keyword
                best_score = 90
        
        # Tier 4: Job title tokens subset of keyword (88)
        elif job_tokens.issubset(keyword_tokens):
            if best_score < 88:
                best_match = keyword
                best_score = 88
        
        # Tier 5: Partial overlap 50%+ (85)
        else:
            overlap = len(job_tokens & keyword_tokens)
            min_tokens = min(len(job_tokens), len(keyword_tokens))
            if min_tokens > 0 and (overlap / min_tokens) >= 0.5:
                if best_score < 85:
                    best_match = keyword
                    best_score = 85
    
    if best_match:
        return (best_match, best_score)
    
    return (None, 0)


def extract_all_jobs(page: Page, keywords: List[str]) -> List[Tuple[str, str, str, str, int]]:
    """
    Extract all job listings from the table and match against keywords.
    
    Args:
        page: Playwright page object
        keywords: List of keywords to match against
    
    Returns:
        List of tuples: (job_id, job_title, department, location, matched_keyword, match_score)
    """
    matched_jobs = []
    
    try:
        # Wait for the results table
        page.wait_for_selector('table#results_list_table tbody tr', timeout=TIMEOUT)
        
        # Get all job rows
        job_rows = page.locator('table#results_list_table tbody tr').all()
        total_jobs = len(job_rows)
        logger.info(f"  📋 Found {total_jobs} total jobs in table")
        
        for row in job_rows:
            try:
                # Extract job ID from tr id attribute
                job_id = row.get_attribute('id')
                
                # Get all td elements
                cells = row.locator('td').all()
                
                if len(cells) < 4:
                    continue
                
                # Extract job details
                adv_number = cells[0].inner_text().strip()
                job_title = cells[1].inner_text().strip()
                department = cells[2].inner_text().strip()
                location = cells[3].inner_text().strip()
                
                # Token match against keywords
                matched_keyword, match_score = token_match_title(job_title, keywords)
                
                if matched_keyword and match_score >= 85:
                    matched_jobs.append((job_id, job_title, department, location, matched_keyword, match_score))
                    logger.info(f"  ✓ MATCH: '{job_title}' → '{matched_keyword}' (score: {match_score})")
            
            except Exception as e:
                logger.warning(f"  ⚠ Error extracting job from row: {e}")
                continue
        
        logger.info(f"  ✓ Matched {len(matched_jobs)} jobs out of {total_jobs}")
        
    except Exception as e:
        logger.error(f"  ✗ Error extracting jobs: {e}")
    
    return matched_jobs


def scrape_job(page: Page, job_id: str, job_title: str, department: str, location: str, 
               matched_keyword: str, match_score: int) -> Optional[MANJob]:
    """
    Scrape a single job by clicking its row and extracting details.
    
    Args:
        page: Playwright page object
        job_id: Job ID from table row
        job_title: Job title
        department: Department name
        location: Location
        matched_keyword: Keyword that matched
        match_score: Match score
    
    Returns:
        MANJob object if successful, None otherwise
    """
    try:
        logger.info(f"  📄 Parsing job: {job_title}")
        
        # Click the job row to load details (use attribute selector since IDs start with numbers)
        page.locator(f'tr[id="{job_id}"]').click()
        
        # Wait for the bulletin div to be visible
        page.wait_for_selector('div#bulletin', timeout=TIMEOUT)
        
        # Small delay for JavaScript to finish
        time.sleep(1)
        
        # Get the job details HTML
        bulletin_html = page.locator('div#bulletin').inner_html()
        
        # Parse the job details
        job = parse_job_details(bulletin_html, job_id, matched_keyword, match_score)
        
        if job:
            # Save HTML for debugging
            html_file = JOBS_HTML_DIR / f"man_job_{job_id}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(bulletin_html)
            logger.debug(f"  💾 Saved HTML: {html_file.name}")
            
            logger.info(f"  ✓ Successfully parsed job {job_id}")
            return job
        
    except Exception as e:
        logger.error(f"  ✗ Error scraping job {job_id}: {e}")
    
    return None


def save_job_to_json(job: MANJob) -> None:
    """
    Save job data to JSON file.
    
    Args:
        job: MANJob object to save
    """
    try:
        job_id = job.scraping_metadata.job_id
        json_file = JOBS_JSON_DIR / f"man_job_{job_id}.json"
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(job.to_dict(), f, indent=4, ensure_ascii=False)
        
        logger.info(f"  💾 Saved JSON: {json_file.name}")
    
    except Exception as e:
        logger.error(f"  ✗ Error saving job to JSON: {e}")


def main():
    """
    Main scraper function.
    """
    logger.info("=" * 80)
    logger.info("Manitoba Government Job Scraper")
    logger.info("=" * 80)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data directory: {JOBS_JSON_DIR.parent}")
    logger.info(f"Headless mode: {HEADLESS}")
    logger.info("=" * 80)
    
    # Load keywords
    keywords = load_keywords()
    if not keywords:
        logger.error("✗ No keywords loaded. Exiting.")
        return
    
    logger.info(f"🔍 Loaded {len(keywords)} keywords for token matching")
    logger.info("=" * 80)
    
    # Track scraped jobs
    scraped_jobs = []
    skipped_duplicates = 0
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Navigate to job search page
            logger.info(f"🌐 Loading: {SEARCH_URL}")
            page.goto(SEARCH_URL)
            page.wait_for_load_state('networkidle')
            
            # Extract all jobs and match against keywords
            logger.info("📋 Extracting all jobs from table...")
            matched_jobs = extract_all_jobs(page, keywords)
            
            if not matched_jobs:
                logger.info("ℹ️  No matching jobs found")
                return
            
            logger.info(f"✓ Found {len(matched_jobs)} matching jobs")
            logger.info("=" * 80)
            
            # Scrape each matched job
            for i, (job_id, job_title, dept, loc, matched_kw, score) in enumerate(matched_jobs, 1):
                # Check for duplicates
                json_file = JOBS_JSON_DIR / f"man_job_{job_id}.json"
                if json_file.exists():
                    logger.info(f"⏭️  [{i}/{len(matched_jobs)}] Skipping duplicate job {job_id}: {job_title}")
                    skipped_duplicates += 1
                    continue
                
                logger.info(f"📋 [{i}/{len(matched_jobs)}] Scraping: {job_title}")
                
                try:
                    job = scrape_job(page, job_id, job_title, dept, loc, matched_kw, score)
                    
                    if job:
                        save_job_to_json(job)
                        scraped_jobs.append(job)
                        logger.info(f"✓ [{i}/{len(matched_jobs)}] Successfully scraped job {job_id}")
                    else:
                        logger.warning(f"⚠ [{i}/{len(matched_jobs)}] Failed to parse job {job_id}")
                
                except Exception as e:
                    logger.error(f"✗ [{i}/{len(matched_jobs)}] Error scraping job {job_id}: {e}")
                
                # Delay between jobs
                if i < len(matched_jobs):
                    delay = random.uniform(*DELAY_BETWEEN_JOBS)
                    time.sleep(delay)
            
        except Exception as e:
            logger.error(f"✗ Fatal error: {e}")
        
        finally:
            browser.close()
    
    # Summary
    logger.info("=" * 80)
    logger.info("Scraping Complete")
    logger.info("=" * 80)
    logger.info(f"Matching jobs found: {len(matched_jobs)}")
    logger.info(f"New jobs scraped: {len(scraped_jobs)}")
    logger.info(f"Duplicates skipped: {skipped_duplicates}")
    logger.info(f"JSON files saved: {JOBS_JSON_DIR}")
    logger.info(f"HTML files saved: {JOBS_HTML_DIR}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 80)
    logger.info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
