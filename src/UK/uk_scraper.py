"""
UK Job Scraper for findajob.dwp.gov.uk
"""

import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, List
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from fuzzywuzzy import fuzz

from src.UK.config import (
    SEARCH_URL,
    LOCATION_CODE,
    RESULTS_PER_PAGE,
    HEADLESS,
    TIMEOUT,
    MATCH_THRESHOLD,
    KEYWORDS,
    DELAY_BETWEEN_SEARCHES,
    DELAY_BETWEEN_PAGES,
    DELAY_BETWEEN_JOBS,
    DATA_DIR,
    HTML_DIR,
    JSON_DIR,
    SEARCH_HTML_DIR,
    LOGS_DIR,
    SCRAPER_VERSION
)
from src.UK.parser import parse_job_details, extract_job_count, parse_search_results
from src.UK.models import UKScrapingMetadata

# Set up logging
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_filename = LOGS_DIR / f"uk_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create data directories
HTML_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)
SEARCH_HTML_DIR.mkdir(parents=True, exist_ok=True)


def load_existing_job_ids() -> set:
    """
    Load job IDs from existing JSON files to prevent re-scraping.
    
    Returns:
        Set of job IDs that have already been scraped
    """
    existing_ids = set()
    if JSON_DIR.exists():
        for json_file in JSON_DIR.glob("*.json"):
            # Extract job_id from filename (e.g., "12345.json" -> "12345")
            job_id = json_file.stem
            existing_ids.add(job_id)
    
    logger.info(f"📂 Found {len(existing_ids)} previously scraped jobs")
    return existing_ids


def token_match_title(job_title: str, keywords: list) -> Tuple[Optional[str], int]:
    """
    Check if job title matches keywords using token-based fuzzy matching.
    
    Args:
        job_title: The job title to check
        keywords: List of keywords to match against
        
    Returns:
        Tuple of (matched_keyword, match_score) or (None, 0) if no match
    """
    title_lower = job_title.lower()
    best_match = None
    best_score = 0
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        
        # Token set ratio for fuzzy matching
        score = fuzz.token_set_ratio(title_lower, keyword_lower)
        
        if score > best_score:
            best_score = score
            best_match = keyword
    
    if best_score >= MATCH_THRESHOLD:
        return best_match, best_score
    
    return None, 0


def search_jobs(page, keyword: str) -> Tuple[int, List[dict]]:
    """
    Search for jobs by keyword and collect all matching results.
    
    Args:
        page: Playwright page object
        keyword: Search keyword
        
    Returns:
        Tuple of (total_jobs, filtered_jobs_list)
    """
    try:
        logger.info(f"🔍 Searching for: '{keyword}'")
        
        # Navigate to search page
        logger.info(f"  🌐 Navigating to search page...")
        page.goto(SEARCH_URL, timeout=TIMEOUT, wait_until="domcontentloaded")
        time.sleep(2)
        
        # Enter search keyword
        logger.info(f"  ⌨️  Entering search keyword: '{keyword}'")
        search_input = page.locator('input[name="q"]#what')
        search_input.wait_for(state="visible", timeout=TIMEOUT)
        search_input.fill(keyword)
        logger.info(f"    ✓ Keyword entered")
        
        # Set location code (UK-wide) - try different selector patterns
        logger.info(f"  📍 Setting location: UK-wide (code: {LOCATION_CODE})")
        try:
            # Try various location input selectors
            location_input = page.locator('input[name="loc"]').first
            if location_input.count() == 0:
                location_input = page.locator('input#where').first
            
            if location_input.count() > 0:
                location_input.fill(LOCATION_CODE)
                logger.info(f"    ✓ Location entered")
            else:
                logger.info(f"    ⚠️  Location field not found, skipping...")
        except Exception as e:
            logger.warning(f"    ⚠️  Could not set location: {e}")
        
        # Submit search - try multiple selectors
        logger.info(f"  🚀 Submitting search...")
        try:
            # Try the submit button
            submit_btn = page.locator('input[type="submit"]').first
            if submit_btn.count() == 0:
                submit_btn = page.locator('button[type="submit"]').first
            
            if submit_btn.count() > 0:
                logger.info(f"    ✓ Submit button found, clicking...")
                submit_btn.click()
            else:
                # Alternative: press Enter on the search input
                logger.info(f"    ⚠️  Submit button not found, pressing Enter instead...")
                search_input.press("Enter")
        except Exception as e:
            logger.warning(f"    ⚠️  Click failed, pressing Enter: {e}")
            search_input.press("Enter")
        
        # Wait for results to load
        logger.info(f"    ⏳ Waiting for search results...")
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        time.sleep(2)
        logger.info(f"    ✓ Search results loaded")
        
        # Set results per page to maximum (50)
        try:
            logger.info(f"  ⚙️  Setting results per page to {RESULTS_PER_PAGE}...")
            per_page_select = page.locator('select#per_page')
            per_page_select.select_option(str(RESULTS_PER_PAGE))
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)
            logger.info(f"  ✓ Results per page set successfully")
        except Exception as e:
            logger.warning(f"  ⚠️  Could not set results per page: {e}")
        
        # Save search results HTML
        html_content = page.content()
        search_file = SEARCH_HTML_DIR / f"{keyword.replace(' ', '_')}_page1.html"
        search_file.write_text(html_content, encoding='utf-8')
        logger.info(f"  💾 Saved search HTML: {search_file.name}")
        
        # Extract total job count
        total_jobs = extract_job_count(html_content)
        logger.info(f"  📊 Found {total_jobs} total jobs for '{keyword}'")
        
        # Parse jobs from first page
        all_jobs = parse_search_results(html_content)
        logger.info(f"  📋 Parsed {len(all_jobs)} jobs from page 1")
        
        # Handle pagination
        page_num = 2
        while True:
            try:
                # Check for next page link
                next_link = page.locator('a.pager-next')
                if next_link.count() == 0:
                    logger.info(f"  ✓ No more pages to process")
                    break
                
                logger.info(f"  📄 Navigating to page {page_num}...")
                next_link.click()
                page.wait_for_load_state("domcontentloaded")
                time.sleep(DELAY_BETWEEN_PAGES)
                
                # Save page HTML
                html_content = page.content()
                search_file = SEARCH_HTML_DIR / f"{keyword.replace(' ', '_')}_page{page_num}.html"
                search_file.write_text(html_content, encoding='utf-8')
                logger.info(f"    💾 Saved: {search_file.name}")
                
                # Parse jobs from current page
                page_jobs = parse_search_results(html_content)
                logger.info(f"    📋 Parsed {len(page_jobs)} jobs from page {page_num}")
                all_jobs.extend(page_jobs)
                
                page_num += 1
                
            except Exception as e:
                logger.info(f"  ✓ Reached last page or error: {e}")
                break
        
        logger.info(f"  ✓ Total jobs collected across all pages: {len(all_jobs)}")
        
        # Filter jobs using fuzzy matching
        logger.info(f"  🔬 Applying fuzzy matching filter (threshold: {MATCH_THRESHOLD})...")
        filtered_jobs = []
        for job in all_jobs:
            matched_keyword, match_score = token_match_title(job['job_title'], KEYWORDS)
            if matched_keyword:
                job['matched_keyword'] = matched_keyword
                job['match_score'] = match_score
                filtered_jobs.append(job)
                logger.info(f"    ✓ Match: '{job['job_title']}' -> {matched_keyword} (score: {match_score})")
        
        logger.info(f"  📊 Filtered to {len(filtered_jobs)} relevant jobs out of {len(all_jobs)} total")
        
        return total_jobs, filtered_jobs
        
    except Exception as e:
        logger.error(f"Error searching for '{keyword}': {str(e)}")
        return 0, []


def scrape_job_details(page, job_info: dict, search_keyword: str, existing_ids: set) -> bool:
    """
    Scrape detailed information for a specific job.
    
    Args:
        page: Playwright page object
        job_info: Dictionary with job_id, job_url, matched_keyword, match_score
        search_keyword: The original search keyword
        existing_ids: Set of job IDs already scraped (for cross-session checking)
        
    Returns:
        True if successful, False otherwise
    """
    job_id = job_info['job_id']
    job_url = job_info['job_url']
    
    # Check if already scraped in previous session
    if job_id in existing_ids:
        logger.info(f"⏭️  Job {job_id} already scraped previously, skipping...")
        return True  # Return True since it's already scraped
    
    try:
        logger.info(f"🔗 Opening job {job_id}: {job_info.get('job_title', 'Unknown')}")
        
        # Navigate to job detail page
        logger.info(f"  🌐 Loading job page...")
        page.goto(job_url, timeout=TIMEOUT, wait_until="domcontentloaded")
        time.sleep(2)
        
        # Get page HTML
        html_content = page.content()
        
        # Save HTML
        html_file = HTML_DIR / f"{job_id}.html"
        html_file.write_text(html_content, encoding='utf-8')
        logger.info(f"  💾 Saved HTML: {html_file.name}")
        
        # Parse job details
        logger.info(f"  📝 Parsing job details...")
        job = parse_job_details(
            html_content,
            job_url,
            job_id,
            search_keyword,
            job_info['matched_keyword'],
            job_info['match_score']
        )
        
        if job:
            # Save as JSON
            json_file = JSON_DIR / f"{job_id}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(job.__dict__, f, indent=2, ensure_ascii=False)
            logger.info(f"  💾 Saved JSON: {json_file.name}")
            
            logger.info(f"  ✓ Successfully scraped: {job.job_title}")
            return True
        else:
            logger.warning(f"  ⚠️  Failed to parse job {job_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error scraping job {job_id}: {str(e)}")
        return False


def main():
    """
    Main scraper function - orchestrates the entire scraping process.
    """
    start_time = time.time()
    metadata = UKScrapingMetadata(
        scrape_date=datetime.now().isoformat(),
        keywords_searched=[],
        total_jobs_found=0,
        jobs_scraped=0,
        jobs_filtered=0,
        errors=[],
        duration_seconds=0
    )
    
    logger.info("=" * 80)
    logger.info("Starting UK Job Scraper")
    logger.info(f"Version: {SCRAPER_VERSION}")
    logger.info(f"Keywords to search: {len(KEYWORDS)}")
    logger.info(f"Match threshold: {MATCH_THRESHOLD}")
    logger.info(f"Headless mode: {HEADLESS}")
    logger.info("=" * 80)
    
    # Load existing job IDs to prevent re-scraping
    existing_job_ids = load_existing_job_ids()
    
    with sync_playwright() as p:
        logger.info("Launching browser...")
        browser = p.chromium.launch(
            headless=HEADLESS,
            slow_mo=500 if not HEADLESS else 0  # Slow down actions in headed mode for visibility
        )
        logger.info("Browser launched successfully")
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        logger.info("Browser page created")
        
        all_filtered_jobs = []
        
        # Search for each keyword
        logger.info("\n" + "=" * 80)
        logger.info("📍 STEP 1: Searching for jobs by keyword")
        logger.info("=" * 80)
        
        for i, keyword in enumerate(KEYWORDS, 1):
            logger.info(f"\n[{i}/{len(KEYWORDS)}] Processing keyword: '{keyword}'")
            logger.info("-" * 80)
            metadata.keywords_searched.append(keyword)
            
            try:
                total_jobs, filtered_jobs = search_jobs(page, keyword)
                metadata.total_jobs_found += total_jobs
                
                # Track unique jobs (avoid duplicates across keywords AND previous sessions)
                new_jobs = []
                session_ids = {job['job_id'] for job in all_filtered_jobs}  # Jobs found in this session
                
                skipped_existing = 0
                skipped_duplicate = 0
                
                for job in filtered_jobs:
                    job_id = job['job_id']
                    
                    # Check if already scraped in previous session
                    if job_id in existing_job_ids:
                        skipped_existing += 1
                        continue
                    
                    # Check if already found in this session
                    if job_id in session_ids:
                        skipped_duplicate += 1
                        continue
                    
                    # New job - add it
                    job['search_keyword'] = keyword
                    new_jobs.append(job)
                    all_filtered_jobs.append(job)
                    session_ids.add(job_id)
                
                logger.info(f"  📊 New unique jobs from this keyword: {len(new_jobs)}")
                if skipped_existing > 0:
                    logger.info(f"  ⏭️  Skipped {skipped_existing} jobs already scraped in previous sessions")
                if skipped_duplicate > 0:
                    logger.info(f"  ⏭️  Skipped {skipped_duplicate} duplicate jobs from earlier keywords")
                
                # Scrape details for new jobs
                if new_jobs:
                    logger.info(f"  🔍 Scraping details for {len(new_jobs)} jobs...")
                    for idx, job in enumerate(new_jobs, 1):
                        logger.info(f"\n    [{idx}/{len(new_jobs)}] Job {job['job_id']}")
                        success = scrape_job_details(page, job, keyword, existing_job_ids)
                        if success:
                            metadata.jobs_scraped += 1
                            # Add to existing_ids so we don't re-scrape if it appears again
                            existing_job_ids.add(job['job_id'])
                        else:
                            metadata.errors.append(f"Failed to scrape job {job['job_id']}")
                        
                        time.sleep(DELAY_BETWEEN_JOBS)
                
                # Delay between keyword searches
                if i < len(KEYWORDS):
                    logger.info(f"\n  ⏳ Waiting {DELAY_BETWEEN_SEARCHES}s before next keyword...")
                    time.sleep(DELAY_BETWEEN_SEARCHES)
                
            except Exception as e:
                error_msg = f"Error processing keyword '{keyword}': {str(e)}"
                logger.error(error_msg)
                metadata.errors.append(error_msg)
        
        browser.close()
    
    # Calculate final statistics
    metadata.jobs_filtered = len(all_filtered_jobs)
    metadata.duration_seconds = int(time.time() - start_time)
    
    # Save metadata
    metadata_file = DATA_DIR / f"metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata.__dict__, f, indent=2, ensure_ascii=False)
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("SCRAPING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Keywords searched: {len(metadata.keywords_searched)}")
    logger.info(f"Total jobs found: {metadata.total_jobs_found}")
    logger.info(f"Jobs passing filter: {metadata.jobs_filtered}")
    logger.info(f"Jobs successfully scraped: {metadata.jobs_scraped}")
    logger.info(f"Errors encountered: {len(metadata.errors)}")
    logger.info(f"Duration: {metadata.duration_seconds} seconds")
    logger.info(f"Log file: {log_filename}")
    logger.info(f"Metadata file: {metadata_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
