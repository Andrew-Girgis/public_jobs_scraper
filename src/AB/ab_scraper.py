"""
Alberta Public Service Job Scraper

Scrapes job postings from https://jobpostings.alberta.ca/
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Set, Optional, Dict, Tuple
from datetime import datetime
from dataclasses import asdict
from playwright.sync_api import sync_playwright, Page, Browser
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from src.AB import config
from src.AB.models import ABJob, ABScrapingMetadata
from src.AB.parser import parse_job_details

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "AB"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"ab_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "AB"
HTML_DIR = DATA_DIR / "job_html"
JSON_DIR = DATA_DIR / "jobs_json"
SEARCH_HTML_DIR = DATA_DIR / "search_html"

# Create directories
HTML_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)
SEARCH_HTML_DIR.mkdir(parents=True, exist_ok=True)


def token_match_title(job_title: str, keywords: List[str]) -> Tuple[Optional[str], int]:
    """
    Find the best matching keyword for a job title using fuzzy matching.
    
    Args:
        job_title: The job title to match
        keywords: List of keywords to match against
        
    Returns:
        Tuple of (matched_keyword, match_score)
        Returns (None, 0) if no good match found
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
    
    # Only return matches with score >= 80 (slightly lower than BC's 85 due to Alberta's longer titles)
    if best_score >= 80:
        return best_match, best_score
    
    return None, 0


def search_by_keyword(page: Page, keyword: str) -> List[Dict[str, str]]:
    """
    Search for jobs by keyword and extract all job links from all pages.
    
    Args:
        page: Playwright Page instance
        keyword: Search keyword
    
    Returns:
        List of dictionaries with job_id, url, title, location, date
    """
    logger.info(f"Searching for keyword: '{keyword}'")
    
    try:
        # Navigate to home page
        page.goto(config.BASE_URL, timeout=30000)
        page.wait_for_timeout(2000)
        
        # Find and fill search box
        search_box = page.locator('input[name="q"].keywordsearch-q')
        search_box.fill(keyword)
        
        # Click search button
        search_button = page.locator('input.keywordsearch-button[type="submit"]')
        search_button.click()
        
        # Wait for results to load
        page.wait_for_timeout(config.PAGE_LOAD_WAIT * 1000)
        
        # Check if there are any results
        try:
            page.wait_for_selector('#searchresults', timeout=5000)
        except:
            logger.info(f"No results found for keyword: '{keyword}'")
            return []
        
        # Extract pagination info
        all_jobs = []
        page_num = 1
        
        while True:
            logger.info(f"Processing page {page_num} for keyword: '{keyword}'")
            
            # Save search results HTML for debugging
            search_html_path = SEARCH_HTML_DIR / f"search_{keyword.replace(' ', '_')}_page{page_num}.html"
            with open(search_html_path, 'w', encoding='utf-8') as f:
                f.write(page.content())
            
            # Parse current page
            soup = BeautifulSoup(page.content(), 'html.parser')
            results_table = soup.find('table', id='searchresults')
            
            if not results_table:
                logger.info(f"No results table found on page {page_num}")
                break
            
            # Extract job links from current page
            rows = results_table.find_all('tr', class_='data-row')
            logger.info(f"Found {len(rows)} jobs on page {page_num}")
            
            for row in rows:
                try:
                    # Extract job link
                    link_elem = row.find('a', class_='jobTitle-link')
                    if not link_elem:
                        continue
                    
                    job_url = config.BASE_URL + link_elem['href']
                    job_title = link_elem.text.strip()
                    
                    # Extract job ID from URL (e.g., /job/Edmonton-Project-Data-Analyst/597090317/)
                    job_id = job_url.rstrip('/').split('/')[-1]
                    
                    # Extract location
                    location_elem = row.find('span', class_='jobLocation')
                    location = location_elem.text.strip() if location_elem else None
                    
                    # Extract posting date
                    date_elem = row.find('span', class_='jobDate')
                    posting_date = date_elem.text.strip() if date_elem else None
                    
                    all_jobs.append({
                        'job_id': job_id,
                        'url': job_url,
                        'title': job_title,
                        'location': location,
                        'posting_date': posting_date,
                        'keyword': keyword
                    })
                    
                except Exception as e:
                    logger.error(f"Error parsing job row: {e}")
                    continue
            
            # Check if there's a next page by clicking the pagination link
            try:
                # Look for the next page number link using Playwright
                next_page_num = page_num + 1
                next_page_selector = f'ul.pagination a[title="Page {next_page_num}"]'
                
                # Check if the next page link exists (use first() since there are two pagination sections)
                if page.locator(next_page_selector).count() > 0:
                    logger.info(f"Navigating to page {next_page_num} by clicking pagination link")
                    
                    # Click the first next page link (top pagination)
                    page.locator(next_page_selector).first.click()
                    
                    # Wait for the page to load
                    page.wait_for_timeout(config.PAGE_LOAD_WAIT * 1000)
                    
                    # Wait for results table to appear
                    try:
                        page.wait_for_selector('#searchresults', timeout=5000)
                    except:
                        logger.warning(f"No results table found after clicking to page {next_page_num}")
                        break
                    
                    page_num = next_page_num
                else:
                    logger.info(f"No more pages found for keyword: '{keyword}'")
                    break
                
            except Exception as e:
                logger.error(f"Error navigating to next page: {e}")
                break
        
        logger.info(f"Found {len(all_jobs)} total jobs for keyword: '{keyword}'")
        return all_jobs
        
    except Exception as e:
        logger.error(f"Error searching for keyword '{keyword}': {e}")
        return []


def extract_all_jobs_from_searches(page: Page, keywords: List[str]) -> List[Dict[str, str]]:
    """
    Search for all keywords and deduplicate results.
    
    Args:
        page: Playwright Page instance
        keywords: List of search keywords
    
    Returns:
        Deduplicated list of job dictionaries
    """
    all_jobs = []
    seen_job_ids: Set[str] = set()
    
    for keyword in keywords:
        jobs = search_by_keyword(page, keyword)
        
        for job in jobs:
            job_id = job['job_id']
            if job_id not in seen_job_ids:
                seen_job_ids.add(job_id)
                all_jobs.append(job)
            else:
                logger.debug(f"Skipping duplicate job: {job_id}")
    
    logger.info(f"Total unique jobs found: {len(all_jobs)}")
    return all_jobs


def scrape_job_details(page: Page, job_info: Dict[str, str], index: int, total: int) -> Optional[ABJob]:
    """
    Scrape detailed information for a single job.
    
    Args:
        page: Playwright Page instance
        job_info: Dictionary with job_id, url, title, etc.
        index: Current job index (for logging)
        total: Total number of jobs (for logging)
    
    Returns:
        ABJob object or None if scraping fails
    """
    job_id = job_info['job_id']
    url = job_info['url']
    
    logger.info(f"[{index}/{total}] Scraping job {job_id}: {job_info['title']}")
    
    try:
        # Navigate to job page
        page.goto(url, timeout=30000)
        page.wait_for_timeout(2000)
        
        # Wait for job content to load
        page.wait_for_selector('.jobDisplay', timeout=10000)
        
        # Get page HTML
        html_content = page.content()
        
        # Save raw HTML
        html_path = HTML_DIR / f"ab_job_{job_id}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Saved HTML to {html_path}")
        
        # Parse job details
        soup = BeautifulSoup(html_content, 'html.parser')
        job_posting = parse_job_details(soup, url, job_info['keyword'])
        
        # Calculate fuzzy match score for job title against ALL keywords
        job_title = job_posting.job_information.job_title
        
        # Skip if job title is missing
        if not job_title:
            logger.warning(f"⚠️  Skipping job {job_id}: Missing job title")
            return None
        
        matched_keyword, match_score = token_match_title(job_title, config.KEYWORDS)
        
        # Filter out jobs with low relevance score
        if match_score < 80:
            logger.info(f"⚠️  Skipping job (low relevance): '{job_title}' - Score: {match_score} (searched: {job_info['keyword']})")
            return None
        
        logger.info(f"✓ Job matched: '{job_title}' - Score: {match_score} - Keyword: '{matched_keyword}'")
        
        # Create job object with metadata
        job = ABJob(
            job_posting=job_posting,
            scraping_metadata=ABScrapingMetadata(
                job_id=job_id,
                matched_keyword=job_info['keyword'],
                match_score=match_score
            )
        )
        
        # Save as JSON
        json_path = JSON_DIR / f"ab_job_{job_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(job), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved JSON to {json_path}")
        
        return job
        
    except Exception as e:
        logger.error(f"Error scraping job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main scraper function."""
    logger.info("=" * 80)
    logger.info("Alberta Public Service Job Scraper")
    logger.info("=" * 80)
    logger.info(f"Base URL: {config.BASE_URL}")
    logger.info(f"Keywords: {len(config.KEYWORDS)}")
    logger.info(f"Output directories:")
    logger.info(f"  HTML: {HTML_DIR}")
    logger.info(f"  JSON: {JSON_DIR}")
    logger.info(f"  Search HTML: {SEARCH_HTML_DIR}")
    logger.info(f"  Logs: {LOG_FILE}")
    logger.info("")
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Search for all jobs
            logger.info("Starting job search across all keywords...")
            all_jobs = extract_all_jobs_from_searches(page, config.KEYWORDS)
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("Search Results Summary")
            logger.info("=" * 80)
            logger.info(f"Keywords searched: {len(config.KEYWORDS)}")
            logger.info(f"Unique jobs found: {len(all_jobs)}")
            logger.info("")
            
            # Scrape each job
            logger.info("Starting detailed job scraping...")
            logger.info("")
            
            success_count = 0
            error_count = 0
            filtered_count = 0
            
            for i, job_info in enumerate(all_jobs, 1):
                job = scrape_job_details(page, job_info, i, len(all_jobs))
                if job:
                    success_count += 1
                elif job is None:
                    # Check if None due to filtering or error
                    # If scrape_job_details returned None after successful parse, it was filtered
                    filtered_count += 1
                else:
                    error_count += 1
                
                # Be respectful with rate limiting
                time.sleep(1)
            
            # Final summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("Scraping Complete")
            logger.info("=" * 80)
            logger.info(f"Jobs found in search: {len(all_jobs)}")
            logger.info(f"Successfully scraped: {success_count}")
            logger.info(f"Filtered (low relevance): {filtered_count}")
            logger.info(f"Errors: {error_count}")
            logger.info("")
            logger.info(f"Relevance rate: {success_count}/{len(all_jobs)} ({100*success_count/len(all_jobs):.1f}%)")
            logger.info("")
            
        finally:
            browser.close()
            logger.info("Browser closed")


if __name__ == "__main__":
    main()
