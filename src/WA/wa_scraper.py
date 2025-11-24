"""
Unified WA Government Jobs Scraper with AI Extraction
https://search.jobs.wa.gov.au

Workflow: Search → Fuzzy Match → Scrape → AI Extract → Save → Next Job
"""

import json
import logging
import time
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
from fuzzywuzzy import fuzz
import openai
from dotenv import load_dotenv

# Handle both direct execution and package imports
try:
    from . import config
    from .models import WAJob, WAScrapingMetadata
    from .parser import parse_search_results
    from .extract_with_ai import extract_job_data_with_ai
except ImportError:
    import config
    from models import WAJob, WAScrapingMetadata
    from parser import parse_search_results
    from extract_with_ai import extract_job_data_with_ai

# Load environment variables
load_dotenv(config.PROJECT_ROOT / ".env")

# Get OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

openai.api_key = OPENAI_API_KEY

# Setup logging
log_file = config.LOGS_DIR / f"wa_scraper_unified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
        logger.error(f"❌ Keywords file not found: {keywords_file}")
        return []
    
    with open(keywords_file, 'r', encoding='utf-8') as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    logger.info(f"✅ Loaded {len(keywords)} keywords from {keywords_file.name}")
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
    logger.info(f"🔍 Searching for: '{keyword}'")
    
    try:
        # Navigate to search page
        page.goto(config.SEARCH_URL, wait_until="load", timeout=30000)
        time.sleep(config.PAGE_DELAY)
        
        # Find search input and enter keyword
        search_input = page.locator('input[name="Advert[Data]"]')
        search_input.fill(keyword)
        time.sleep(config.REQUEST_DELAY)
        
        # Click search button
        search_button = page.locator('input#searchButton')
        search_button.click()
        
        # Wait for results to load
        time.sleep(config.PAGE_DELAY + 1)
        
        # Get HTML
        html = page.content()
        
        # Save search HTML
        search_file = config.SEARCH_HTML_DIR / f"{keyword.replace(' ', '_').replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(search_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"   💾 Search HTML saved: {search_file.name}")
        return html
        
    except Exception as e:
        logger.error(f"   ❌ Error searching for '{keyword}': {str(e)}")
        return ""


def scrape_job_html(page: Page, job_url: str, job_id: str) -> Optional[str]:
    """
    Scrape HTML of a job posting.
    
    Args:
        page: Playwright page object
        job_url: Relative or full URL to job
        job_id: Job ID (AdvertID)
    
    Returns:
        HTML content of job details page, or None on error
    """
    # Make URL absolute if needed
    if not job_url.startswith('http'):
        full_url = f"{config.BASE_URL}/{job_url}"
    else:
        full_url = job_url
    
    logger.info(f"      📄 Scraping HTML from: {full_url}")
    
    try:
        page.goto(full_url, wait_until="load", timeout=30000)
        time.sleep(config.JOB_DELAY)
        
        html = page.content()
        
        # Save job HTML
        html_file = config.JOB_HTML_DIR / f"{job_id}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"      ✅ HTML saved: {html_file.name}")
        return html
        
    except PlaywrightTimeout:
        logger.warning(f"      ⚠️  Timeout loading job page: {full_url}")
        return None
    except Exception as e:
        logger.error(f"      ❌ Error scraping job {job_id}: {str(e)}")
        return None


def extract_job_data(html: str, job_id: str, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract job data using AI.
    
    Args:
        html: HTML content of job page
        job_id: Job ID
        job_data: Basic job data from search results
    
    Returns:
        Dictionary with extracted job data, or None on error
    """
    logger.info(f"      🤖 Extracting data with AI for job {job_id}...")
    
    try:
        extracted_data = extract_job_data_with_ai(html, job_id)
        
        if not extracted_data:
            logger.error(f"      ❌ AI extraction returned no data for job {job_id}")
            return None
        
        # Validate extracted data
        required_fields = ['description_html', 'description_text']
        missing_fields = [field for field in required_fields if not extracted_data.get(field)]
        
        if missing_fields:
            logger.warning(f"      ⚠️  Missing fields from AI extraction: {', '.join(missing_fields)}")
        
        # Log what was extracted
        has_salary = bool(extracted_data.get('salary'))
        has_description = bool(extracted_data.get('description_html'))
        has_attachments = len(extracted_data.get('attachments', [])) > 0
        
        logger.info(f"      ✅ AI extraction complete:")
        logger.info(f"         - Salary: {'✓' if has_salary else '✗'}")
        logger.info(f"         - Description: {'✓' if has_description else '✗'}")
        logger.info(f"         - Attachments: {len(extracted_data.get('attachments', []))}")
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"      ❌ Error in AI extraction for job {job_id}: {str(e)}")
        return None


def save_job_data(job_data: WAJob) -> bool:
    """
    Save job data to JSON file.
    
    Args:
        job_data: WAJob object to save
    
    Returns:
        True if successful, False otherwise
    """
    try:
        json_file = config.JOBS_JSON_DIR / f"{job_data.job_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(job_data.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"      💾 Job saved: {json_file.name}")
        return True
        
    except Exception as e:
        logger.error(f"      ❌ Error saving job data: {str(e)}")
        return False


def scrape_all(max_jobs: Optional[int] = None):
    """
    Main unified scraping function.
    
    Workflow: Search → Fuzzy Match → Scrape → AI Extract → Save → Next Job
    
    Args:
        max_jobs: Maximum number of jobs to scrape (for testing)
    """
    start_time = time.time()
    
    logger.info("\n" + "="*80)
    logger.info("🚀 STARTING WA GOVERNMENT JOBS SCRAPER (UNIFIED WITH AI EXTRACTION)")
    logger.info("="*80 + "\n")
    
    # Load keywords
    keywords = load_keywords()
    
    if not keywords:
        logger.error("❌ No keywords loaded. Exiting.")
        return
    
    # Stats
    stats = {
        'keywords_searched': 0,
        'total_jobs_found': 0,
        'jobs_matched': 0,
        'jobs_scraped': 0,
        'ai_extractions_successful': 0,
        'ai_extractions_failed': 0,
        'jobs_saved': 0,
        'errors': 0,
        'filtered_low_match': 0,
        'filtered_duplicate': 0
    }
    
    scraped_job_ids: Set[str] = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Phase 1: Search and collect matched jobs
            logger.info("\n" + "="*80)
            logger.info("PHASE 1: SEARCHING AND FUZZY MATCHING")
            logger.info("="*80 + "\n")
            
            matched_jobs = []
            
            for keyword_idx, keyword in enumerate(keywords, 1):
                logger.info(f"\n[{keyword_idx}/{len(keywords)}] Keyword: '{keyword}'")
                logger.info("-" * 60)
                
                try:
                    # Search for keyword
                    search_html = search_jobs(page, keyword)
                    
                    if not search_html:
                        logger.warning(f"   ⚠️  No HTML returned for search")
                        stats['errors'] += 1
                        continue
                    
                    # Parse search results
                    jobs = parse_search_results(search_html)
                    stats['total_jobs_found'] += len(jobs)
                    
                    logger.info(f"   📋 Found {len(jobs)} jobs")
                    
                    # Fuzzy match each job
                    for job_idx, job_data in enumerate(jobs, 1):
                        job_id = job_data['job_id']
                        job_title = job_data['job_title']
                        
                        # Skip duplicates
                        if job_id in scraped_job_ids:
                            logger.debug(f"      [{job_idx}/{len(jobs)}] ⏭️  Duplicate: {job_title} (ID: {job_id})")
                            stats['filtered_duplicate'] += 1
                            continue
                        
                        # Fuzzy match
                        matched_keyword, match_score = fuzzy_match_keyword(job_title, keywords, config.MATCH_THRESHOLD)
                        
                        if not matched_keyword:
                            logger.debug(f"      [{job_idx}/{len(jobs)}] ⏭️  Low match ({match_score}%): {job_title[:50]}...")
                            stats['filtered_low_match'] += 1
                            continue
                        
                        # Add to matched jobs list
                        job_data['search_keyword'] = keyword
                        job_data['matched_keyword'] = matched_keyword
                        job_data['match_score'] = match_score
                        matched_jobs.append(job_data)
                        scraped_job_ids.add(job_id)
                        stats['jobs_matched'] += 1
                        
                        logger.info(f"      [{job_idx}/{len(jobs)}] ✅ Match ({match_score}%): {job_title[:60]}...")
                    
                    stats['keywords_searched'] += 1
                    
                except Exception as e:
                    logger.error(f"   ❌ Error processing keyword '{keyword}': {str(e)}")
                    stats['errors'] += 1
                    continue
            
            # Phase 2: Scrape and extract with AI
            logger.info("\n" + "="*80)
            logger.info(f"PHASE 2: SCRAPING AND AI EXTRACTION ({len(matched_jobs)} jobs)")
            logger.info("="*80 + "\n")
            
            for job_idx, job_data in enumerate(matched_jobs, 1):
                # Check max_jobs limit
                if max_jobs and stats['jobs_scraped'] >= max_jobs:
                    logger.info(f"\n✅ Reached max_jobs limit ({max_jobs}). Stopping.")
                    break
                
                job_id = job_data['job_id']
                job_title = job_data['job_title']
                
                logger.info(f"\n[{job_idx}/{len(matched_jobs)}] Processing: {job_title}")
                logger.info(f"   Job ID: {job_id}")
                logger.info(f"   Match: {job_data['matched_keyword']} ({job_data['match_score']}%)")
                
                try:
                    # Step 1: Scrape HTML
                    job_html = scrape_job_html(page, job_data['job_url'], job_id)
                    
                    if not job_html:
                        logger.error(f"      ❌ Failed to scrape HTML")
                        stats['errors'] += 1
                        continue
                    
                    stats['jobs_scraped'] += 1
                    
                    # Step 2: Extract with AI
                    extracted_data = extract_job_data(job_html, job_id, job_data)
                    
                    if not extracted_data:
                        logger.error(f"      ❌ AI extraction failed")
                        stats['ai_extractions_failed'] += 1
                        continue
                    
                    stats['ai_extractions_successful'] += 1
                    
                    # Step 3: Create WAJob object
                    wa_job = WAJob(
                        job_id=job_id,
                        position_number=extracted_data.get('position_number') or job_data.get('position_number', ''),
                        job_title=job_title,
                        job_url=f"{config.BASE_URL}/{job_data['job_url']}" if not job_data['job_url'].startswith('http') else job_data['job_url'],
                        agency=extracted_data.get('agency') or job_data.get('agency', ''),
                        branch=extracted_data.get('branch') or job_data.get('branch'),
                        location=extracted_data.get('location') or job_data.get('location', ''),
                        classification=extracted_data.get('classification') or job_data.get('classification', ''),
                        posting_date=job_data.get('posting_date', ''),
                        closing_date=extracted_data.get('closing_date') or job_data.get('closing_date', ''),
                        division_name=extracted_data.get('division_name'),
                        job_type=extracted_data.get('job_type'),
                        salary=extracted_data.get('salary'),
                        description_html=extracted_data.get('description_html', ''),
                        description_text=extracted_data.get('description_text'),
                        attachments=extracted_data.get('attachments', []),
                        search_keyword=job_data['search_keyword'],
                        matched_keyword=job_data['matched_keyword'],
                        match_score=job_data['match_score'],
                        scraped_at=datetime.now().isoformat(),
                        scraper_version=config.SCRAPER_VERSION
                    )
                    
                    # Step 4: Save to JSON
                    if save_job_data(wa_job):
                        stats['jobs_saved'] += 1
                    else:
                        stats['errors'] += 1
                    
                except Exception as e:
                    logger.error(f"      ❌ Error processing job {job_id}: {str(e)}")
                    stats['errors'] += 1
                    continue
            
        finally:
            browser.close()
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Save metadata
    metadata = WAScrapingMetadata(
        scrape_date=datetime.now().isoformat(),
        keywords_searched=stats['keywords_searched'],
        total_jobs_found=stats['total_jobs_found'],
        jobs_scraped=stats['jobs_saved'],
        jobs_filtered=stats['filtered_low_match'] + stats['filtered_duplicate'],
        errors=stats['errors'],
        duration_seconds=round(duration, 2)
    )
    
    metadata_file = config.DATA_DIR / f"scraping_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata.to_dict(), f, indent=2)
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("📊 FINAL SUMMARY")
    logger.info("="*80)
    logger.info(f"Keywords searched: {stats['keywords_searched']}/{len(keywords)}")
    logger.info(f"Total jobs found: {stats['total_jobs_found']}")
    logger.info(f"Jobs matched (fuzzy): {stats['jobs_matched']}")
    logger.info(f"Jobs scraped (HTML): {stats['jobs_scraped']}")
    logger.info(f"AI extractions successful: {stats['ai_extractions_successful']}")
    logger.info(f"AI extractions failed: {stats['ai_extractions_failed']}")
    logger.info(f"Jobs saved: {stats['jobs_saved']}")
    logger.info(f"")
    logger.info(f"Filtered (low match): {stats['filtered_low_match']}")
    logger.info(f"Filtered (duplicates): {stats['filtered_duplicate']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info(f"")
    logger.info(f"Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
    logger.info(f"Success rate: {(stats['ai_extractions_successful']/max(stats['jobs_scraped'], 1)*100):.1f}%")
    logger.info(f"")
    logger.info(f"Metadata saved: {metadata_file}")
    logger.info(f"Log file: {log_file}")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified WA Government Jobs Scraper with AI Extraction")
    parser.add_argument('--max-jobs', type=int, help='Maximum number of jobs to scrape (for testing)')
    args = parser.parse_args()
    
    scrape_all(max_jobs=args.max_jobs)
