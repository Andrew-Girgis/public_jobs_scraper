"""
Tasmania Government Job Scraper

Scrapes job postings from https://www.jobs.tas.gov.au/
"""

import json
import time
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Set
from playwright.sync_api import sync_playwright, Page
from fuzzywuzzy import fuzz

from . import config, parser
from .models import TASJob, TASScrapingMetadata


# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KEYWORDS_FILE = PROJECT_ROOT / config.KEYWORDS_FILE
DATA_DIR = PROJECT_ROOT / config.DATA_DIR
JOBS_JSON_DIR = PROJECT_ROOT / config.JOBS_JSON_DIR
JOB_HTML_DIR = PROJECT_ROOT / config.JOB_HTML_DIR
SEARCH_HTML_DIR = PROJECT_ROOT / config.SEARCH_HTML_DIR
LOGS_DIR = PROJECT_ROOT / config.LOGS_DIR

# Create directories
for directory in [DATA_DIR, JOBS_JSON_DIR, JOB_HTML_DIR, SEARCH_HTML_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Set up logging
log_filename = LOGS_DIR / f"tas_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_existing_job_ids() -> set:
    """Load job IDs that have already been scraped."""
    existing_ids = set()
    
    if JOBS_JSON_DIR.exists():
        for json_file in JOBS_JSON_DIR.glob("*.json"):
            existing_ids.add(json_file.stem)
    
    return existing_ids


def token_match_title(job_title: str, keywords: List[str]) -> Tuple[bool, str, int]:
    """
    Check if job title matches any keyword using token-based fuzzy matching.
    
    Args:
        job_title: Job title to check
        keywords: List of keywords to match against
    
    Returns:
        Tuple of (matches, matched_keyword, score)
    """
    best_match = ""
    best_score = 0
    
    for keyword in keywords:
        score = fuzz.token_set_ratio(keyword.lower(), job_title.lower())
        if score > best_score:
            best_score = score
            best_match = keyword
    
    matches = best_score >= config.MATCH_THRESHOLD
    return matches, best_match, best_score


def search_jobs(page: Page, keyword: str) -> Tuple[int, List[dict]]:
    """
    Search for jobs with given keyword and load all results using "More jobs" button.
    
    Args:
        page: Playwright page object
        keyword: Search keyword
    
    Returns:
        Tuple of (total_count, list of job dicts)
    """
    logger.info(f"\n🔍 Searching for: '{keyword}'")
    
    # Navigate to search page
    page.goto(config.SEARCH_URL, wait_until="networkidle")
    time.sleep(1)
    
    # Fill search input
    search_input = page.locator('input#jobSearch_search-keyword')
    search_input.fill(keyword)
    time.sleep(0.5)
    
    # Click search button
    search_button = page.locator('input[type="submit"].submit-button')
    search_button.click()
    
    # Wait for results
    page.wait_for_load_state("networkidle")
    time.sleep(config.SEARCH_DELAY)
    
    all_jobs = []
    page_num = 1
    
    while True:
        # Save search HTML
        html_content = page.content()
        search_html_file = SEARCH_HTML_DIR / f"{keyword.replace(' ', '_')}_page{page_num}.html"
        with open(search_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Parse current page results
        jobs = parser.parse_search_results(html_content)
        logger.info(f"   📄 Page {page_num}: Found {len(jobs)} jobs")
        all_jobs.extend(jobs)
        
        # Check for "More jobs" button - it loads content via AJAX, not navigation
        # We need to scroll to it and wait for it to be clickable
        try:
            # Look for visible "More jobs" button
            more_button = page.locator('a.more-link.button:visible').first
            
            if more_button.count() > 0:
                print(f"   ⏩ Loading more jobs...")
                
                # Scroll the button into view
                more_button.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                
                # Click the button to trigger AJAX load
                more_button.click()
                
                # Wait for new content to load
                page.wait_for_timeout(2000)  # Give AJAX time to load
                page.wait_for_load_state("networkidle")
                time.sleep(config.PAGE_DELAY)
                page_num += 1
            else:
                logger.info(f"   ✅ All pages loaded ({page_num} pages total)")
                break
        except Exception as e:
            logger.warning(f"   ⚠️  No more content to load: {str(e)}")
            logger.info(f"   ✅ All pages loaded ({page_num} pages total)")
            break
    
    logger.info(f"   📊 Total jobs found: {len(all_jobs)}")
    
    return len(all_jobs), all_jobs


def scrape_job_details(
    page: Page,
    job_info: dict,
    search_keyword: str,
    existing_ids: Set[str]
) -> bool:
    """
    Scrape details for a single job.
    
    Args:
        page: Playwright page object
        job_info: Job info dict with id, title, url
        search_keyword: Keyword used in search
        existing_ids: Set of already scraped job IDs
    
    Returns:
        True if successful, False otherwise
    """
    job_id = job_info['job_id']
    job_title = job_info['job_title']
    job_url = job_info['job_url']
    
    # Check if already scraped
    if job_id in existing_ids:
        logger.info(f"   ⏭️  Job {job_id} already scraped previously, skipping...")
        return True
    
    try:
        logger.info(f"   🔄 Scraping: {job_title[:60]}... (ID: {job_id})")
        
        # Navigate to job page
        page.goto(job_url, wait_until="networkidle")
        time.sleep(config.JOB_DELAY)
        
        # Get page HTML
        html_content = page.content()
        
        # Save job HTML
        job_html_file = JOB_HTML_DIR / f"{job_id}.html"
        with open(job_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Parse job details
        scraped_at = datetime.now().isoformat()
        
        # Get match info (already filtered, so we know it matches)
        keywords = []
        if KEYWORDS_FILE.exists():
            with open(KEYWORDS_FILE, 'r') as f:
                keywords = [line.strip() for line in f if line.strip()]
        
        matches, matched_keyword, match_score = token_match_title(job_title, keywords)
        
        job = parser.parse_job_details(
            html_content=html_content,
            job_url=job_url,
            job_id=job_id,
            job_title=job_title,
            search_keyword=search_keyword,
            matched_keyword=matched_keyword,
            match_score=match_score,
            scraper_version=config.SCRAPER_VERSION,
            scraped_at=scraped_at
        )
        
        if not job:
            logger.error(f"   ❌ Failed to parse job {job_id}")
            return False
        
        # Save as JSON
        job_json_file = JOBS_JSON_DIR / f"{job_id}.json"
        with open(job_json_file, 'w', encoding='utf-8') as f:
            json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Saved: {job_title[:60]}... (Match: {match_score}, Agency: {job.agency})")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error scraping job {job_id}: {str(e)}")
        return False


def run_scraper():
    """Main scraper function"""
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("🦘 Tasmania Government Job Scraper")
    logger.info("=" * 80)
    logger.info(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🌐 Target: {config.BASE_URL}")
    logger.info(f"📊 Match threshold: {config.MATCH_THRESHOLD}")
    logger.info(f"📝 Log file: {log_filename}")
    logger.info("")
    
    # Load keywords
    if not KEYWORDS_FILE.exists():
        logger.error(f"❌ Keywords file not found: {KEYWORDS_FILE}")
        return
    
    with open(KEYWORDS_FILE, 'r') as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    logger.info(f"📋 Loaded {len(keywords)} keywords from {config.KEYWORDS_FILE}")
    logger.info("")
    
    # Load existing job IDs (for cross-session duplicate prevention)
    existing_job_ids = load_existing_job_ids()
    logger.info(f"📂 Found {len(existing_job_ids)} previously scraped jobs")
    logger.info("")
    
    # Track jobs found in this session (for within-session duplicate prevention)
    session_job_ids = set()
    
    # Statistics
    total_jobs_found = 0
    jobs_scraped = 0
    jobs_filtered = 0
    errors = []
    
    # Launch browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Search for each keyword
            for i, keyword in enumerate(keywords, 1):
                logger.info(f"[{i}/{len(keywords)}] Processing keyword: '{keyword}'")
                
                try:
                    # Search and get all results
                    count, jobs = search_jobs(page, keyword)
                    total_jobs_found += count
                    
                    # Filter jobs with fuzzy matching
                    matched_jobs = []
                    for job in jobs:
                        matches, matched_keyword, match_score = token_match_title(
                            job['job_title'], 
                            keywords
                        )
                        
                        if matches:
                            job['matched_keyword'] = matched_keyword
                            job['match_score'] = match_score
                            matched_jobs.append(job)
                        else:
                            jobs_filtered += 1
                    
                    logger.info(f"   ✅ {len(matched_jobs)} jobs passed fuzzy matching (filtered {len(jobs) - len(matched_jobs)})")
                    
                    # Scrape matched jobs
                    for job in matched_jobs:
                        job_id = job['job_id']
                        
                        # Check if already found in this session
                        if job_id in session_job_ids:
                            logger.info(f"   ⏭️  Job {job_id} already found in this session, skipping...")
                            continue
                        
                        # Scrape job details
                        success = scrape_job_details(
                            page=page,
                            job_info=job,
                            search_keyword=keyword,
                            existing_ids=existing_job_ids
                        )
                        
                        if success:
                            jobs_scraped += 1
                            session_job_ids.add(job_id)
                        else:
                            errors.append(f"Failed to scrape job {job_id}")
                    
                    logger.info("")
                    
                except Exception as e:
                    error_msg = f"Error processing keyword '{keyword}': {str(e)}"
                    logger.error(f"   ❌ {error_msg}")
                    errors.append(error_msg)
                    logger.info("")
        
        finally:
            browser.close()
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Save metadata
    metadata = TASScrapingMetadata(
        scrape_date=datetime.now().isoformat(),
        keywords_searched=keywords,
        total_jobs_found=total_jobs_found,
        jobs_scraped=jobs_scraped,
        jobs_filtered=jobs_filtered,
        errors=errors,
        duration_seconds=duration
    )
    
    metadata_file = DATA_DIR / f"metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
    
    # Print summary
    logger.info("=" * 80)
    logger.info("📊 Scraping Summary")
    logger.info("=" * 80)
    logger.info(f"⏱️  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logger.info(f"🔍 Keywords searched: {len(keywords)}")
    logger.info(f"📊 Total jobs found: {total_jobs_found}")
    logger.info(f"✅ Jobs scraped: {jobs_scraped}")
    logger.info(f"🔄 Jobs filtered out: {jobs_filtered}")
    logger.info(f"❌ Errors: {len(errors)}")
    logger.info(f"💾 Data saved to: {DATA_DIR}")
    logger.info("=" * 80)


if __name__ == "__main__":
    run_scraper()
