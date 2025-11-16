"""
Queensland Government Job Scraper

Scrapes job postings from https://smartjobs.qld.gov.au/
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
from .models import QLDJob, QLDScrapingMetadata


# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KEYWORDS_FILE = PROJECT_ROOT / config.KEYWORDS_FILE
DATA_DIR = config.DATA_DIR
JOBS_JSON_DIR = config.JOBS_JSON_DIR
JOB_HTML_DIR = config.JOB_HTML_DIR
SEARCH_HTML_DIR = config.SEARCH_HTML_DIR
LOGS_DIR = config.LOGS_DIR

# Set up logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_filename = LOGS_DIR / f"qld_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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
    Search for jobs with given keyword and navigate through all pages.
    
    Args:
        page: Playwright page object
        keyword: Search keyword
    
    Returns:
        Tuple of (total_count, list of job dicts)
    """
    logger.info(f"\n🔍 Searching for: '{keyword}'")
    
    # Navigate to search page - use 'load' from the start
    page.goto(config.SEARCH_URL, wait_until="load", timeout=20000)
    time.sleep(1)
    
    # Fill search input
    search_input = page.locator('input#in_skills')
    search_input.fill(keyword)
    time.sleep(0.5)
    
    # Click search button
    search_button = page.locator('input[type="submit"]#searchBtn')
    search_button.click()
    
    # Wait for results - use 'load' state (faster)
    page.wait_for_load_state("load", timeout=20000)
    time.sleep(config.PAGE_DELAY)
    
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
        
        # Check for next page button
        if parser.has_next_page(html_content):
            try:
                logger.info(f"   ⏩ Loading page {page_num + 1}...")
                
                # Click the "Next" button
                next_button = page.locator('input[name="in_storeNextBut"][value="Next"]')
                next_button.click()
                
                # Wait for next page - use 'load' state (faster)
                page.wait_for_load_state("load", timeout=20000)
                time.sleep(config.PAGE_DELAY)
                page_num += 1
            except Exception as e:
                logger.warning(f"   ⚠️  Error loading next page: {str(e)}")
                logger.info(f"   ✅ All pages loaded ({page_num} pages total)")
                break
        else:
            logger.info(f"   ✅ All pages loaded ({page_num} pages total)")
            break
    
    logger.info(f"   📊 Total jobs found: {len(all_jobs)}")
    
    return len(all_jobs), all_jobs


def scrape_job_details(
    page: Page,
    job_info: dict,
    search_keyword: str,
    existing_ids: Set[str],
    session_ids: Set[str]
) -> bool:
    """
    Scrape details for a single job.
    
    Args:
        page: Playwright page object
        job_info: Job info dict with id, title, url
        search_keyword: Keyword used in search
        existing_ids: Set of already scraped job IDs (from disk)
        session_ids: Set of job IDs scraped in this session
    
    Returns:
        True if successful, False otherwise
    """
    job_id = job_info['job_id']
    job_title = job_info['job_title']
    job_url = job_info['job_url']
    
    # Check if already scraped (cross-session)
    if job_id in existing_ids:
        logger.info(f"   ⏭️  Job {job_id} already scraped previously, skipping...")
        return True
    
    # Check if already found in this session
    if job_id in session_ids:
        logger.info(f"   ⏭️  Job {job_id} already found in this session, skipping...")
        return True
    
    try:
        logger.info(f"   🔄 Scraping: {job_title[:60]}... (ID: {job_id})")
        
        # Navigate to job page - use 'load' from the start (faster and more reliable)
        page.goto(job_url, wait_until="load", timeout=20000)
        
        # Give page a moment to settle (much faster than networkidle)
        time.sleep(1)
        
        # Get page HTML
        html_content = page.content()
        
        # Save job HTML
        job_html_file = JOB_HTML_DIR / f"{job_id}.html"
        with open(job_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Parse job details
        scraped_at = datetime.now().isoformat()
        
        # Get match info
        keywords = []
        if KEYWORDS_FILE.exists():
            with open(KEYWORDS_FILE, 'r') as f:
                keywords = [line.strip() for line in f if line.strip()]
        
        matches, matched_keyword, match_score = token_match_title(job_title, keywords)
        
        # Parse full job details
        job_details = parser.parse_job_details(html_content, job_info)
        
        if not job_details:
            logger.error(f"      ❌ Failed to parse job details for {job_id}")
            return False
        
        # Create job object
        job = QLDJob(
            job_id=job_id,
            job_reference=job_details.get('job_reference'),
            job_title=job_details.get('job_title', job_title),
            job_url=job_url,
            organization=job_details.get('organization'),
            department=job_details.get('department'),
            location=job_details.get('location'),
            position_status=job_details.get('position_status'),
            position_type=job_details.get('position_type'),
            occupational_group=job_details.get('occupational_group'),
            classification=job_details.get('classification'),
            closing_date=job_details.get('closing_date'),
            date_posted=job_details.get('date_posted'),
            salary_yearly=job_details.get('salary_yearly'),
            salary_fortnightly=job_details.get('salary_fortnightly'),
            total_remuneration=job_details.get('total_remuneration'),
            summary=job_details.get('summary'),
            description_html=job_details.get('description_html', ''),
            contact_person=job_details.get('contact_person'),
            contact_details=job_details.get('contact_details'),
            search_keyword=search_keyword,
            matched_keyword=matched_keyword,
            match_score=match_score,
            scraped_at=scraped_at,
            scraper_version=config.SCRAPER_VERSION
        )
        
        # Save as JSON
        job_json_file = JOBS_JSON_DIR / f"{job_id}.json"
        with open(job_json_file, 'w', encoding='utf-8') as f:
            json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"      ✅ Saved job {job_id}")
        
        # Add to session IDs
        session_ids.add(job_id)
        
        return True
        
    except Exception as e:
        logger.error(f"      ❌ Error scraping job {job_id}: {str(e)}")
        return False


def scrape_all():
    """Main function to scrape all jobs."""
    start_time = time.time()
    
    logger.info("🦘 Queensland Government Job Scraper")
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
    
    logger.info(f"📋 Loaded {len(keywords)} keywords from {KEYWORDS_FILE.name}")
    logger.info("")
    
    # Load existing job IDs
    existing_ids = load_existing_job_ids()
    logger.info(f"📂 Found {len(existing_ids)} previously scraped jobs")
    logger.info("")
    
    # Track session
    session_ids = set()
    total_found = 0
    total_scraped = 0
    total_filtered = 0
    errors = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            for idx, keyword in enumerate(keywords, 1):
                logger.info(f"[{idx}/{len(keywords)}] Processing keyword: '{keyword}'")
                
                try:
                    # Search for jobs
                    count, jobs = search_jobs(page, keyword)
                    total_found += count
                    
                    if count == 0:
                        logger.warning(f"   ⚠️  No jobs found for '{keyword}'")
                        continue
                    
                    # Filter jobs using fuzzy matching
                    matched_jobs = []
                    for job in jobs:
                        matches, matched_kw, score = token_match_title(
                            job['job_title'],
                            keywords
                        )
                        if matches:
                            job['matched_keyword'] = matched_kw
                            job['match_score'] = score
                            matched_jobs.append(job)
                    
                    filtered_count = len(jobs) - len(matched_jobs)
                    total_filtered += filtered_count
                    
                    logger.info(f"   ✅ {len(matched_jobs)} jobs passed fuzzy matching (filtered {filtered_count})")
                    
                    # Scrape each job's details
                    for job in matched_jobs:
                        success = scrape_job_details(
                            page,
                            job,
                            keyword,
                            existing_ids,
                            session_ids
                        )
                        if success:
                            total_scraped += 1
                        else:
                            errors.append(f"Failed to scrape job {job['job_id']}")
                        
                        time.sleep(config.REQUEST_DELAY)
                    
                except Exception as e:
                    error_msg = f"Error processing keyword '{keyword}': {str(e)}"
                    logger.error(f"   ❌ {error_msg}")
                    errors.append(error_msg)
                    continue
        
        finally:
            browser.close()
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Print summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 Scraping Summary")
    logger.info("=" * 80)
    logger.info(f"Keywords searched: {len(keywords)}")
    logger.info(f"Total jobs found: {total_found}")
    logger.info(f"Jobs filtered out: {total_filtered}")
    logger.info(f"Jobs scraped: {total_scraped}")
    logger.info(f"Errors: {len(errors)}")
    logger.info(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    logger.info("=" * 80)
    
    # Save metadata
    metadata = QLDScrapingMetadata(
        scrape_date=datetime.now().isoformat(),
        keywords_searched=keywords,
        total_jobs_found=total_found,
        jobs_scraped=total_scraped,
        jobs_filtered=total_filtered,
        errors=errors,
        duration_seconds=duration
    )
    
    metadata_file = DATA_DIR / f"metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n✅ Metadata saved to {metadata_file}")


if __name__ == "__main__":
    scrape_all()
