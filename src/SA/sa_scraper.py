"""
Web scraper for South Australia Government Jobs
https://iworkfor.sa.gov.au
"""

import json
import logging
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Set
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from fuzzywuzzy import fuzz

from . import config
from .models import SAJob, SAScrapingMetadata
from .parser import parse_search_results, parse_job_details

# Setup logging
log_file = config.LOGS_DIR / f"sa_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_keywords() -> List[str]:
    """Load search keywords from file"""
    keywords_file = config.PROJECT_ROOT / config.KEYWORDS_FILE
    
    if not keywords_file.exists():
        logger.error(f"Keywords file not found: {keywords_file}")
        return []
    
    with open(keywords_file, 'r', encoding='utf-8') as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Loaded {len(keywords)} keywords from {keywords_file.name}")
    return keywords


def fuzzy_match_keyword(job_title: str, keywords: List[str], threshold: int = 80) -> tuple:
    """
    Check if job title matches any keyword using fuzzy matching.
    
    Args:
        job_title: Job title to check
        keywords: List of keywords to match against
        threshold: Minimum match score (0-100)
    
    Returns:
        Tuple of (matched_keyword, match_score) or (None, 0)
    """
    best_match = None
    best_score = 0
    
    for keyword in keywords:
        score = fuzz.partial_ratio(keyword.lower(), job_title.lower())
        if score > best_score:
            best_score = score
            best_match = keyword
    
    if best_score >= threshold:
        return best_match, best_score
    
    return None, 0


def search_jobs(page: Page, keyword: str) -> str:
    """
    Perform search for a keyword and return HTML.
    
    Args:
        page: Playwright page object
        keyword: Search keyword
    
    Returns:
        HTML content of search results
    """
    logger.info(f"🔍 Searching for: {keyword}")
    
    # Navigate to search page
    page.goto(config.SEARCH_URL, wait_until="load", timeout=60000)
    time.sleep(config.PAGE_DELAY)
    
    # Find search input and enter keyword
    search_input = page.locator('input[name="Advert[Data]"]')
    search_input.fill(keyword)
    time.sleep(config.REQUEST_DELAY)
    
    # Click search button
    search_button = page.locator('input#brsSearchBtn')
    search_button.click()
    
    # Wait for results to load
    time.sleep(config.PAGE_DELAY + 3)  # SA pages take longer to load
    
    # Get HTML
    html = page.content()
    
    # Save search HTML
    search_file = config.SEARCH_HTML_DIR / f"{keyword.replace(' ', '_').replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(search_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html


def scrape_job_details(page: Page, job_url: str, job_id: str) -> str:
    """
    Scrape full details of a job posting.
    
    Args:
        page: Playwright page object
        job_url: Relative or full URL to job
        job_id: Job ID (AdvertID)
    
    Returns:
        HTML content of job details page
    """
    # Make URL absolute if needed
    if not job_url.startswith('http'):
        full_url = f"{config.BASE_URL}/{job_url}"
    else:
        full_url = job_url
    
    logger.debug(f"   📄 Scraping job details: {full_url}")
    
    try:
        page.goto(full_url, wait_until="load", timeout=60000)
        time.sleep(config.JOB_DELAY + 1)  # SA job pages load slowly
        
        html = page.content()
        
        # Save job HTML
        html_file = config.JOB_HTML_DIR / f"{job_id}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return html
        
    except PlaywrightTimeout:
        logger.warning(f"   ⚠️  Timeout loading job page: {full_url}")
        return ""
    except Exception as e:
        logger.error(f"   ❌ Error scraping job {job_id}: {str(e)}")
        return ""


def main():
    """
    Main scraping function.
    """
    start_time = time.time()
    keywords = load_keywords()
    
    if not keywords:
        logger.error("No keywords loaded. Exiting.")
        return
    
    # Stats
    total_jobs_found = 0
    jobs_scraped = 0
    jobs_filtered = 0
    errors = 0
    scraped_job_ids: Set[str] = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            for keyword_idx, keyword in enumerate(keywords, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"Keyword {keyword_idx}/{len(keywords)}: {keyword}")
                logger.info(f"{'='*60}")
                
                try:
                    # Search for keyword
                    search_html = search_jobs(page, keyword)
                    
                    # Parse search results
                    jobs = parse_search_results(search_html)
                    total_jobs_found += len(jobs)
                    
                    logger.info(f"📋 Found {len(jobs)} jobs for '{keyword}'")
                    
                    # Process each job
                    for job_idx, job_data in enumerate(jobs, 1):
                        job_id = job_data['job_id']
                        job_title = job_data['job_title']
                        
                        # Skip if already scraped in this session
                        if job_id in scraped_job_ids:
                            logger.debug(f"   ⏭️  Skipping duplicate: {job_title} (ID: {job_id})")
                            continue
                        
                        # Fuzzy match job title
                        matched_keyword, match_score = fuzzy_match_keyword(job_title, keywords, config.MATCH_THRESHOLD)
                        
                        if not matched_keyword:
                            logger.debug(f"   ⏭️  Skipping (low match): {job_title}")
                            jobs_filtered += 1
                            continue
                        
                        logger.info(f"   [{job_idx}/{len(jobs)}] ✅ Match: {job_title[:60]}... ({match_score}%)")
                        
                        # Scrape job details
                        job_html = scrape_job_details(page, job_data['job_url'], job_id)
                        
                        if not job_html:
                            errors += 1
                            continue
                        
                        # Parse job details
                        details = parse_job_details(job_html)
                        
                        # Create SAJob object
                        sa_job = SAJob(
                            job_id=job_id,
                            reference_number=details.get('reference_number') or job_data['reference_number'],
                            job_title=job_title,
                            job_url=f"{config.BASE_URL}/{job_data['job_url']}",
                            agency=details.get('agency') or job_data['agency'],
                            location=details.get('location', ''),
                            posting_date=job_data['posting_date'],
                            job_status=details.get('job_status'),
                            eligibility=details.get('eligibility'),
                            closing_date=details.get('closing_date', ''),
                            salary=details.get('salary'),
                            description_html=details.get('description_html', ''),
                            description_text=details.get('description_text'),
                            attachments=details.get('attachments', []),
                            search_keyword=keyword,
                            matched_keyword=matched_keyword,
                            match_score=match_score,
                            scraped_at=datetime.now().isoformat(),
                            scraper_version=config.SCRAPER_VERSION
                        )
                        
                        # Save to JSON
                        json_file = config.JOBS_JSON_DIR / f"{job_id}.json"
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(sa_job.to_dict(), f, indent=2, ensure_ascii=False)
                        
                        scraped_job_ids.add(job_id)
                        jobs_scraped += 1
                        
                        logger.info(f"   💾 Saved: {json_file.name}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing keyword '{keyword}': {str(e)}")
                    errors += 1
                    continue
            
        finally:
            browser.close()
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Create metadata
    metadata = SAScrapingMetadata(
        scrape_date=datetime.now().isoformat(),
        keywords_searched=keyword_idx if 'keyword_idx' in locals() else len(keywords),
        total_jobs_found=total_jobs_found,
        jobs_scraped=jobs_scraped,
        jobs_filtered=jobs_filtered,
        errors=errors,
        duration_seconds=round(duration, 2)
    )
    
    # Save metadata
    metadata_file = config.DATA_DIR / f"scraping_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata.to_dict(), f, indent=2)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("📊 SCRAPING SUMMARY")
    logger.info("="*60)
    logger.info(f"Keywords searched: {metadata.keywords_searched}/{len(keywords)}")
    logger.info(f"Total jobs found: {total_jobs_found}")
    logger.info(f"Jobs scraped: {jobs_scraped}")
    logger.info(f"Jobs filtered: {jobs_filtered}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"Metadata saved: {metadata_file}")
    logger.info("="*60)


if __name__ == "__main__":
    main()
