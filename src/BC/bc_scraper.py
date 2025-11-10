"""
BC Public Service Job Scraper

Scrapes job postings from the BC Public Service recruitment system.
Uses "With ALL of the following" search with all keywords at once,
then does token matching to determine best keyword match.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from dataclasses import asdict
from playwright.sync_api import sync_playwright, Page, Browser
from fuzzywuzzy import fuzz

from .config import (
    BASE_URL, SEARCH_URL, HTML_DIR, SEARCH_HTML_DIR, JSON_DIR, LOG_DIR,
    HEADLESS, RESULTS_PER_PAGE, REQUEST_TIMEOUT, PAGE_LOAD_WAIT
)
from .parser import parse_job_details
from .models import BCJob

# Set up logging
log_file = LOG_DIR / f"bc_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    """Load keywords from list-of-jobs.txt"""
    keywords_file = Path(__file__).resolve().parent.parent.parent / "list-of-jobs.txt"
    
    if not keywords_file.exists():
        logger.error(f"Keywords file not found: {keywords_file}")
        return []
    
    keywords = []
    with open(keywords_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                keywords.append(line)
    
    logger.info(f"Loaded {len(keywords)} keywords from {keywords_file.name}")
    return keywords


def token_match_title(job_title: str, keywords: List[str]) -> Tuple[Optional[str], int]:
    """
    Find the best matching keyword for a job title using fuzzy matching.
    
    Returns:
        Tuple of (matched_keyword, match_score)
    """
    job_title_lower = job_title.lower()
    best_match = None
    best_score = 0
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        
        # Exact substring match (100)
        if keyword_lower in job_title_lower:
            return keyword, 100
        
        # Fuzzy matching with different strategies
        # Partial ratio (good for substring matching)
        partial_score = fuzz.partial_ratio(keyword_lower, job_title_lower)
        if partial_score > best_score:
            best_score = partial_score
            best_match = keyword
        
        # Token sort ratio (good for word order independence)
        token_score = fuzz.token_sort_ratio(keyword_lower, job_title_lower)
        if token_score > best_score:
            best_score = token_score
            best_match = keyword
    
    # Only return matches with score >= 85
    if best_score >= 85:
        return best_match, best_score
    
    return None, 0


def search_by_keyword(page: Page, keyword: str) -> List[Dict[str, str]]:
    """
    Perform search for a single keyword and extract job results.
    
    Returns:
        List of job dicts from search results
    """
    logger.info(f"🔍 Searching for: '{keyword}'")
    
    # Navigate to search page (use 'domcontentloaded' instead of 'networkidle' for speed)
    page.goto(SEARCH_URL, timeout=REQUEST_TIMEOUT, wait_until='domcontentloaded')
    
    # Wait for search form to be ready
    page.wait_for_selector('input[name="with_all"]', timeout=5000)
    
    # Fill in search box with keyword
    search_input = page.locator('input[name="with_all"]')
    search_input.fill(keyword)
    
    # Click search button
    search_button = page.locator('button[type="submit"]').first
    search_button.click()
    
    # Wait for EITHER results table OR no-results message (race condition)
    try:
        # Use wait_for_selector with a race - whichever appears first wins
        page.wait_for_selector('table#jobSearchResultsGrid_table tbody tr, em.text-muted:has-text("There is no data to display")', timeout=10000)
        
        # Check which one appeared
        if page.locator('em.text-muted:has-text("There is no data to display")').is_visible():
            logger.info(f"  ✗ No results found for '{keyword}'")
            return []
    except:
        logger.info(f"  ✗ No results found for '{keyword}' (timeout)")
        return []
    
    # Don't bother changing page size - 25 per page is fine for keyword searches
    # Most keyword searches will return < 25 results anyway
    
    # Extract jobs from this search
    jobs = extract_job_links(page)
    
    # Add search keyword to each job
    for job in jobs:
        job['search_keyword'] = keyword
    
    logger.info(f"  ✓ Found {len(jobs)} results for '{keyword}'")
    
    # Save search results HTML (only for searches with results)
    if jobs:
        html_content = page.content()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_keyword = keyword.replace(' ', '_').replace('/', '_')
        search_file = SEARCH_HTML_DIR / f"bc_search_{safe_keyword}_{timestamp}.html"
        search_file.write_text(html_content, encoding='utf-8')
    
    return jobs


def extract_job_links(page: Page) -> List[Dict[str, str]]:
    """
    Extract all job links and basic info from search results table.
    
    Returns:
        List of dicts with job_id, job_title, req_number, ministry, union, location, etc.
    """
    jobs = []
    
    # Find all rows in the table
    rows = page.locator('table#jobSearchResultsGrid_table tbody tr').all()
    logger.info(f"📋 Found {len(rows)} job listings")
    
    for row in rows:
        try:
            # Extract data from table columns
            cells = row.locator('td').all()
            if len(cells) < 8:
                continue
            
            ministry = cells[0].inner_text().strip()
            req_number = cells[1].inner_text().strip()
            
            # Job title is in a link
            title_link = cells[2].locator('a').first
            job_title = title_link.locator('span').inner_text().strip()
            job_url = title_link.get_attribute('href')
            
            # Extract job ID from URL (e.g., /hr/ats/Posting/view/121578)
            job_id = job_url.split('/')[-1] if job_url else None
            
            union = cells[3].inner_text().strip()
            work_options = cells[4].inner_text().strip()
            location = cells[5].inner_text().strip()
            date_opened = cells[6].inner_text().strip()
            close_date = cells[7].inner_text().strip()
            
            jobs.append({
                'job_id': job_id,
                'job_title': job_title,
                'req_number': req_number,
                'ministry': ministry,
                'union': union,
                'work_options': work_options,
                'location': location,
                'date_opened': date_opened,
                'close_date': close_date,
                'url': f"{BASE_URL}{job_url}" if job_url else None
            })
            
        except Exception as e:
            logger.warning(f"⚠️  Error extracting job from row: {e}")
            continue
    
    return jobs


def filter_jobs_by_keywords(jobs: List[Dict], keywords: List[str]) -> List[Dict]:
    """
    Filter jobs by token matching against keywords.
    Adds 'matched_keyword' and 'match_score' to each job.
    
    Returns:
        List of jobs that match keywords
    """
    matched_jobs = []
    
    for job in jobs:
        job_title = job['job_title']
        matched_keyword, match_score = token_match_title(job_title, keywords)
        
        if matched_keyword:
            job['matched_keyword'] = matched_keyword
            job['match_score'] = match_score
            matched_jobs.append(job)
            logger.info(f"  ✓ Match: {job_title} → '{matched_keyword}' ({match_score})")
        else:
            logger.debug(f"  ✗ No match: {job_title}")
    
    return matched_jobs


def scrape_job_details(page: Page, job_info: Dict, keywords: List[str]) -> Optional[BCJob]:
    """
    Scrape detailed information for a single job posting.
    
    Args:
        page: Playwright page object
        job_info: Basic job info dict from search results
        keywords: List of keywords for matching
    
    Returns:
        BCJob object or None if scraping fails
    """
    job_id = job_info['job_id']
    job_url = job_info['url']
    
    try:
        logger.info(f"🔗 Opening job {job_id}: {job_info['job_title']}")
        page.goto(job_url, timeout=REQUEST_TIMEOUT, wait_until='networkidle')
        page.wait_for_timeout(PAGE_LOAD_WAIT)
        
        # Wait for job details to load
        page.wait_for_selector('div#job-detail', timeout=REQUEST_TIMEOUT)
        
        # Get HTML content
        html_content = page.content()
        
        # Save HTML
        html_file = HTML_DIR / f"bc_job_{job_id}.html"
        html_file.write_text(html_content, encoding='utf-8')
        logger.info(f"  💾 Saved HTML: {html_file.name}")
        
        # Parse the job details
        logger.info(f"  📝 Parsing job details...")
        job = parse_job_details(
            html_content,
            job_id,
            job_info['matched_keyword'],
            job_info['match_score']
        )
        
        if job:
            logger.info(f"  ✓ Successfully parsed job {job_id}")
            
            # Save JSON - use asdict() to properly convert dataclasses
            json_file = JSON_DIR / f"bc_job_{job_id}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(job), f, indent=2, default=str)
            logger.info(f"  💾 Saved JSON: {json_file.name}")
            
            return job
        else:
            logger.warning(f"  ⚠️  Failed to parse job {job_id}")
            return None
            
    except Exception as e:
        logger.error(f"  ✗ Error scraping job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main scraper function"""
    logger.info("=" * 80)
    logger.info("BC Public Service Job Scraper")
    logger.info("=" * 80)
    logger.info(f"Headless mode: {HEADLESS}")
    logger.info(f"Results per page: {RESULTS_PER_PAGE}")
    logger.info("")
    
    # Load keywords
    keywords = load_keywords()
    if not keywords:
        logger.error("No keywords loaded. Exiting.")
        return
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        try:
            # Step 1: Search for each keyword
            logger.info("📍 STEP 1: Searching for jobs by keyword")
            logger.info("-" * 80)
            
            all_jobs = []
            seen_job_ids = set()
            
            for i, keyword in enumerate(keywords, 1):
                logger.info(f"[{i}/{len(keywords)}] Searching: '{keyword}'")
                
                jobs = search_by_keyword(page, keyword)
                
                # Deduplicate by job_id
                new_jobs = []
                for job in jobs:
                    if job['job_id'] not in seen_job_ids:
                        seen_job_ids.add(job['job_id'])
                        new_jobs.append(job)
                
                if new_jobs:
                    logger.info(f"  ✓ Added {len(new_jobs)} new unique jobs (total: {len(seen_job_ids)})")
                    all_jobs.extend(new_jobs)
                
                # Small delay between searches (0.5s is enough)
                time.sleep(0.5)
            
            logger.info(f"\n✓ Total unique jobs found: {len(all_jobs)}")
            
            if not all_jobs:
                logger.warning("No jobs found. Exiting.")
                return
            
            # Step 2: Deduplicate and prepare jobs
            logger.info("")
            logger.info("📍 STEP 2: Preparing unique jobs")
            logger.info("-" * 80)
            
            # Use the search keyword as matched keyword for now
            # (since we already searched with it)
            for job in all_jobs:
                if 'matched_keyword' not in job:
                    job['matched_keyword'] = job.get('search_keyword')
                    job['match_score'] = 100  # Exact search match
            
            logger.info(f"✓ {len(all_jobs)} unique jobs ready to scrape")
            
            # Step 3: Scrape each job
            logger.info("")
            logger.info("📍 STEP 3: Scraping job details")
            logger.info("-" * 80)
            
            success_count = 0
            error_count = 0
            
            for i, job_info in enumerate(all_jobs, 1):
                logger.info(f"\n[{i}/{len(all_jobs)}] Processing job {job_info['job_id']}")
                
                # Check if already scraped
                json_file = JSON_DIR / f"bc_job_{job_info['job_id']}.json"
                if json_file.exists():
                    logger.info(f"  ⏭️  Already scraped, skipping")
                    success_count += 1
                    continue
                
                job = scrape_job_details(page, job_info, keywords)
                
                if job:
                    success_count += 1
                    logger.info(f"✓ [{i}/{len(all_jobs)}] Successfully scraped job {job_info['job_id']}")
                else:
                    error_count += 1
                    logger.error(f"✗ [{i}/{len(all_jobs)}] Failed to scrape job {job_info['job_id']}")
                
                # Small delay between jobs
                time.sleep(1)
            
            # Summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("SCRAPING SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Keywords searched: {len(keywords)}")
            logger.info(f"Unique jobs found: {len(all_jobs)}")
            logger.info(f"Successfully scraped: {success_count}")
            logger.info(f"Errors: {error_count}")
            logger.info("")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            browser.close()
            logger.info("✓ Browser closed")


if __name__ == "__main__":
    main()
