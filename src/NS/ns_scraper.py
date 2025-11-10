"""
Nova Scotia (NS) government job scraper.

This module provides functionality to:
1. Search for jobs using keywords from list-of-jobs.txt
2. Extract job listings from search results
3. Navigate through pagination
4. Scrape detailed job postings
5. Save data to JSON files

Architecture matches GOC and ONT scrapers with token-based matching.
"""

import logging
import json
import time
import random
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError

from .config import (
    BASE_URL,
    SEARCH_URL,
    HOME_URL,
    DATA_DIR,
    JOBS_JSON_DIR,
    JOBS_HTML_DIR,
    SEARCH_HTML_DIR,
    LOG_DIR,
    JOB_LIST_FILE,
    HEADLESS,
    TIMEOUT,
    DELAY_BETWEEN_PAGES,
    DELAY_BETWEEN_SEARCHES,
)
from .models import NSJob

# Set up logging
log_file = LOG_DIR / f"ns_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_keywords() -> List[str]:
    """
    Load job keywords from list-of-jobs.txt.
    
    Returns:
        List of keywords to search for
    """
    keywords = []
    
    if not JOB_LIST_FILE.exists():
        logger.error(f"Keywords file not found: {JOB_LIST_FILE}")
        return keywords
    
    with open(JOB_LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            keyword = line.strip()
            if keyword and not keyword.startswith("#"):
                keywords.append(keyword)
    
    logger.info(f"✓ Loaded {len(keywords)} keywords from {JOB_LIST_FILE.name}")
    return keywords


def token_match_title(job_title: str, keywords: List[str]) -> Optional[Tuple[str, float]]:
    """
    Match job title against keywords using token-based matching.
    
    This replaces fuzzy matching with a more precise system:
    1. Exact phrase match (100 points)
    2. All tokens present (95 points)
    3. Single token match (90 points)
    4. Word variation match (88 points)
    5. Special pattern match (85 points)
    
    Args:
        job_title: The job title to match
        keywords: List of keywords/phrases to match against
    
    Returns:
        Tuple of (matched_keyword, score) if match found, None otherwise
    """
    # Normalize the title
    title_lower = job_title.lower()
    title_normalized = title_lower.replace(",", " ").replace("-", " ").replace("(", " ").replace(")", " ")
    title_tokens = set(title_normalized.split())
    
    # Common word variations and synonyms
    word_variations = {
        'economist': ['economic', 'economy', 'economics'],
        'analyst': ['analysis', 'analytical'],
        'manager': ['management', 'managing'],
        'developer': ['development', 'developing'],
        'administrator': ['administration', 'administrative'],
        'coordinator': ['coordination', 'coordinating'],
        'specialist': ['specialization', 'specialized'],
        'officer': ['official'],
        'advisor': ['advisory', 'advising'],
    }
    
    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        
        # Skip empty keywords
        if not keyword_lower:
            continue
        
        # 1. Exact phrase match (substring)
        if keyword_lower in title_lower:
            logger.debug(f"Exact match: '{job_title}' contains '{keyword}' (score: 100)")
            return keyword, 100.0
        
        # 2. Token-based matching for multi-word keywords
        keyword_tokens = keyword_lower.replace(",", " ").replace("-", " ").split()
        
        if len(keyword_tokens) > 1:
            # Check if all keyword tokens are present in the title
            if all(token in title_tokens for token in keyword_tokens):
                logger.debug(f"Token match: '{job_title}' has all tokens from '{keyword}' (score: 95)")
                return keyword, 95.0
        
        # 3. Single-word exact token match
        elif len(keyword_tokens) == 1:
            if keyword_tokens[0] in title_tokens:
                logger.debug(f"Single token match: '{job_title}' contains token '{keyword}' (score: 90)")
                return keyword, 90.0
            
            # 3b. Check for word variations (e.g., "economist" matches "economic")
            if keyword_tokens[0] in word_variations:
                variations = word_variations[keyword_tokens[0]]
                for variation in variations:
                    if variation in title_tokens:
                        logger.debug(f"Variation match: '{job_title}' contains '{variation}' (matches '{keyword}') (score: 88)")
                        return keyword, 88.0
    
    # 4. Special combination patterns (common data/analyst/management roles)
    special_patterns = [
        ({"data", "analyst"}, "Data Analyst"),
        ({"data", "scientist"}, "Data Scientist"),
        ({"information", "management"}, "Information Management"),
        ({"business", "analyst"}, "Business Analyst"),
        ({"policy", "analyst"}, "Policy Analyst"),
        ({"policy", "advisor"}, "Policy Advisor"),
        ({"research", "analyst"}, "Research Analyst"),
        ({"project", "manager"}, "Project Manager"),
        ({"senior", "manager"}, "Senior Manager"),
        ({"cyber", "security"}, "Cyber Security"),
    ]
    
    for required_tokens, pattern_name in special_patterns:
        if required_tokens.issubset(title_tokens):
            logger.debug(f"Pattern match: '{job_title}' matches pattern '{pattern_name}' (score: 85)")
            return pattern_name, 85.0
    
    return None


def extract_job_id_from_url(url: str) -> Optional[str]:
    """
    Extract job ID from Nova Scotia job URL.
    Example: /job/HALIFAX-Senior-Policy-Analyst-NS-B3J2R8/597235617/
    
    Args:
        url: The job URL
    
    Returns:
        Job ID if found, None otherwise
    """
    # Job ID is the last number in the URL path
    match = re.search(r'/(\d+)/?$', url)
    if match:
        return match.group(1)
    return None


def human_like_scroll(page: Page, steps: int = 3) -> None:
    """
    Scroll through the page in a human-like manner.
    
    Args:
        page: Playwright page object
        steps: Number of scroll steps (default: 3)
    """
    try:
        # Get page height
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        
        logger.debug(f"  📜 Scrolling page (height: {page_height}px, viewport: {viewport_height}px)")
        
        # Scroll down in steps
        for i in range(steps):
            # Random scroll distance (30-70% of viewport)
            scroll_amount = int(viewport_height * random.uniform(0.3, 0.7))
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            
            # Random pause between scrolls (0.3-0.8 seconds)
            pause = random.uniform(0.3, 0.8)
            time.sleep(pause)
            
        logger.debug(f"  ✓ Scrolled page in {steps} steps")
    except Exception as e:
        logger.warning(f"  ⚠ Scroll failed: {e}")


def search_jobs(page: Page, keyword: str) -> str:
    """
    Search for jobs using URL parameters (faster than form submission).
    
    Args:
        page: Playwright page object
        keyword: Search keyword
    
    Returns:
        Search results URL
    """
    # Build search URL with parameters
    params = {
        'createNewAlert': 'false',
        'q': keyword,
        'locationsearch': ''
    }
    search_url = f"{SEARCH_URL}?{urlencode(params)}"
    
    logger.info(f"🔍 Searching for: '{keyword}'")
    logger.debug(f"  URL: {search_url}")
    
    # Navigate to search URL
    page.goto(search_url, wait_until="domcontentloaded", timeout=TIMEOUT)
    
    # Wait for results table or no-results message
    try:
        page.wait_for_selector("table#searchresults, .noresults-message", timeout=10000)
    except PlaywrightTimeoutError:
        logger.warning(f"  ⚠ Timeout waiting for search results")
    
    time.sleep(random.uniform(1.5, 2.5))  # Human-like delay
    
    return search_url


def get_total_pages(page: Page) -> int:
    """
    Get total number of pages from pagination.
    
    Args:
        page: Playwright page object
    
    Returns:
        Total number of pages
    """
    try:
        # Look for pagination links
        pagination_links = page.locator(".pagination li:not(.active) a[href*='startrow']").all()
        
        if not pagination_links:
            # Only one page
            return 1
        
        # Extract page numbers from links
        page_numbers = []
        for link in pagination_links:
            href = link.get_attribute("href")
            if href:
                # Extract startrow parameter to calculate page number
                match = re.search(r'startrow=(\d+)', href)
                if match:
                    startrow = int(match.group(1))
                    # Assuming 25 results per page
                    page_num = (startrow // 25) + 1
                    page_numbers.append(page_num)
        
        # Get max page number
        if page_numbers:
            total = max(page_numbers) + 1  # +1 because first page is 1
            logger.info(f"  📄 Total pages: {total}")
            return total
        
        return 1
    except Exception as e:
        logger.warning(f"  ⚠ Error getting total pages: {e}")
        return 1


def navigate_to_page(page: Page, keyword: str, page_num: int) -> None:
    """
    Navigate to specific page number in search results.
    
    Args:
        page: Playwright page object
        keyword: Search keyword
        page_num: Page number to navigate to (1-indexed)
    """
    if page_num == 1:
        return  # Already on first page
    
    # Calculate startrow (0-indexed, 25 results per page)
    startrow = (page_num - 1) * 25
    
    # Build URL with page parameter
    params = {
        'q': keyword,
        'startrow': str(startrow)
    }
    page_url = f"{SEARCH_URL}?{urlencode(params)}"
    
    logger.info(f"  📄 Navigating to page {page_num}")
    logger.debug(f"  URL: {page_url}")
    
    # Scroll to bottom before navigation (human-like)
    try:
        page.evaluate("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })")
        time.sleep(random.uniform(1.0, 2.0))
    except Exception as e:
        logger.warning(f"  ⚠ Scroll failed: {e}")
    
    # Navigate to page
    page.goto(page_url, wait_until="domcontentloaded", timeout=TIMEOUT)
    
    # Wait for results table
    try:
        page.wait_for_selector("table#searchresults", timeout=10000)
    except PlaywrightTimeoutError:
        logger.warning(f"  ⚠ Timeout waiting for page {page_num}")
    
    # Random delay (2-3.5 seconds)
    delay = random.uniform(2.0, 3.5)
    time.sleep(delay)


def extract_job_links(page: Page, current_keyword: str, keywords: List[str]) -> List[Tuple[str, str, str, float]]:
    """
    Extract job links from current search results page with token matching filter.
    
    Uses token-based matching to filter jobs and only scrape relevant positions.
    This saves time and storage by focusing on jobs that match our keyword criteria.
    
    Args:
        page: Playwright page object
        current_keyword: The keyword used for this search
        keywords: Full list of keywords (for token matching)
    
    Returns:
        List of tuples: (job_url, job_title, matched_keyword, match_score)
    """
    job_links = []
    
    try:
        # Check if there are results
        no_results = page.locator(".noresults-message").count() > 0
        if no_results:
            logger.info("  ℹ No results found")
            return job_links
        
        # Find all job rows in the table
        job_rows = page.locator("table#searchresults tbody tr.data-row").all()
        
        if not job_rows:
            logger.warning("  ⚠ No job rows found in table")
            return job_links
        
        logger.info(f"  📋 Found {len(job_rows)} jobs on this page")
        
        for row in job_rows:
            try:
                # Extract job title and link
                title_link = row.locator("a.jobTitle-link").first
                
                if title_link.count() == 0:
                    continue
                
                job_title = title_link.inner_text().strip()
                job_href = title_link.get_attribute("href")
                
                if not job_title or not job_href:
                    continue
                
                # Build full URL
                job_url = urljoin(BASE_URL, job_href)
                
                # Check if title matches any keyword using token matching
                match_result = token_match_title(job_title, keywords)
                
                if match_result:
                    matched_keyword, match_score = match_result
                    job_links.append((job_url, job_title, matched_keyword, match_score))
                    logger.info(f"  ✓ MATCH: '{job_title}' → '{matched_keyword}' (score: {match_score:.0f})")
                else:
                    logger.debug(f"  ✗ No match: '{job_title}'")
                    
            except Exception as e:
                logger.warning(f"  ⚠ Error extracting job from row: {e}")
                continue
        
        logger.info(f"  ✓ Extracted {len(job_links)} matching jobs from page")
        
    except Exception as e:
        logger.error(f"  ✗ Error extracting job links: {e}")
    
    return job_links


def parse_job_page(page: Page, job_url: str, job_title: str, search_keyword: str, matched_keyword: str, match_score: float) -> Optional[NSJob]:
    """
    Parse a job detail page and extract all information.
    
    Args:
        page: Playwright page object
        job_url: URL of the job
        job_title: Job title
        search_keyword: The keyword used in the search query
        matched_keyword: Keyword that matched this job via token matching
        match_score: Match score
    
    Returns:
        NSJob object if successful, None otherwise
    """
    try:
        logger.info(f"  📄 Parsing job: {job_title}")
        
        # Extract job ID from URL
        job_id = extract_job_id_from_url(job_url)
        if not job_id:
            logger.warning(f"  ⚠ Could not extract job ID from URL: {job_url}")
            return None
        
        # Create job object
        job = NSJob(
            job_id=job_id,
            source_url=job_url,
            job_title=job_title,
            search_keyword=search_keyword,
            matched_keyword=matched_keyword,
            match_score=match_score,
            scraped_at=datetime.now()
        )
        
        # Navigate to job page
        page.goto(job_url, wait_until="domcontentloaded", timeout=TIMEOUT)
        time.sleep(random.uniform(1.5, 2.5))
        
        # Scroll through page (human-like)
        human_like_scroll(page, steps=3)
        
        # Save HTML
        html_file = JOBS_HTML_DIR / f"ns_job_{job_id}.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(page.content())
        logger.debug(f"  💾 Saved HTML: {html_file.name}")
        
        # Extract job details from the page
        # (We'll implement detailed parsing in parser.py, for now just basic extraction)
        
        # Extract metadata from job description
        try:
            # Classification (from job title if it has parentheses)
            if "(" in job_title and ")" in job_title:
                match = re.search(r'\(([^)]+)\)', job_title)
                if match:
                    job.classification = match.group(1)
            
            # Get the description span that contains all metadata
            desc_span = page.locator('span[itemprop="description"]').first
            
            if desc_span.count() > 0:
                desc_html = desc_span.inner_html()
                desc_text = desc_span.inner_text()
                
                # Extract fields using regex patterns
                # Competition Number
                comp_match = re.search(r'Competition\s*#?\s*:?\s*(\d+)', desc_text, re.IGNORECASE)
                if comp_match:
                    job.competition_number = comp_match.group(1)
                
                # Department
                dept_match = re.search(r'Department:\s*(.+?)(?:\n|$)', desc_text)
                if dept_match:
                    job.department = dept_match.group(1).strip()
                
                # Location
                loc_match = re.search(r'Location:\s*(.+?)(?:\n|$)', desc_text)
                if loc_match:
                    job.location = loc_match.group(1).strip()
                
                # Type of Employment
                emp_match = re.search(r'Type of Employment:\s*(.+?)(?:\n|$)', desc_text)
                if emp_match:
                    job.type_of_employment = emp_match.group(1).strip()
                
                # Union Status
                union_match = re.search(r'Union Status:\s*(.+?)(?:\n|$)', desc_text)
                if union_match:
                    job.union_status = union_match.group(1).strip()
                
                # Closing Date
                closing_match = re.search(r'Closing Date:\s*[​\s]*(\d{1,2}-[A-Za-z]{3}-\d{2})', desc_text)
                if closing_match:
                    date_text = closing_match.group(1).strip()
                    try:
                        job.closing_date = datetime.strptime(date_text, "%d-%b-%y")
                    except ValueError:
                        logger.warning(f"  ⚠ Could not parse date: {date_text}")
                
                # Pay Grade
                pay_match = re.search(r'Pay Grade:\s*(.+?)(?:\n|$)', desc_text)
                if pay_match:
                    job.pay_grade = pay_match.group(1).strip()
                
                # Salary Range
                salary_match = re.search(r'Salary Range:\s*\$?([\d,]+\.?\d*)\s*-\s*\$?([\d,]+\.?\d*)\s*(Bi-Weekly|Annual|Hourly)?', desc_text)
                if salary_match:
                    job.salary_range_raw_text = salary_match.group(0)
                    try:
                        job.salary_min_amount = float(salary_match.group(1).replace(',', ''))
                        job.salary_max_amount = float(salary_match.group(2).replace(',', ''))
                        if salary_match.group(3):
                            job.salary_frequency = salary_match.group(3)
                    except (ValueError, AttributeError):
                        pass
        
        except Exception as e:
            logger.warning(f"  ⚠ Error extracting metadata: {e}")
        
        # Extract job content sections
        try:
            # The content is in the main description span
            description_span = page.locator('span[itemprop="description"]').first
            
            if description_span.count() > 0:
                # Get all section divs (they have padding:10.0px style)
                section_divs = description_span.locator('div[style*="padding:10.0px"]').all()
                
                logger.debug(f"  Found {len(section_divs)} content sections")
                
                for div in section_divs:
                    try:
                        # Find heading (h2 with b tag inside)
                        heading_elem = div.locator("h2 b, h2 strong").first
                        if heading_elem.count() == 0:
                            continue
                        
                        heading_text = heading_elem.inner_text().strip()
                        
                        # Get the content div that follows the heading div
                        # The structure is: <div><h2>Heading</h2></div><div>Content</div>
                        parent_div = div
                        content_div = parent_div.locator("div").nth(1)  # Second div has content
                        
                        if content_div.count() == 0:
                            continue
                        
                        content = content_div.inner_text().strip()
                        
                        # Remove heading from content if it appears
                        if content.startswith(heading_text):
                            content = content[len(heading_text):].strip()
                        
                        logger.debug(f"  Section: '{heading_text}' ({len(content)} chars)")
                        
                        # Map to appropriate fields
                        if "About Us" in heading_text:
                            job.about_us_body = content
                        elif "About Our Opportunity" in heading_text:
                            job.about_opportunity_body = content
                        elif "Primary Accountabilities" in heading_text:
                            job.primary_accountabilities_intro = content
                            # Extract bullets if present
                            bullets = content_div.locator("li").all()
                            if bullets:
                                job.primary_accountabilities_bullets = [b.inner_text().strip() for b in bullets]
                        elif "Qualifications" in heading_text and "Experience" in heading_text:
                            job.qualifications_requirements_intro = content
                            # Extract bullets for required skills
                            bullets = content_div.locator("li").all()
                            if bullets:
                                job.qualifications_required_bullets = [b.inner_text().strip() for b in bullets]
                        elif "Assets" in heading_text:
                            # Extract asset bullets
                            bullets = content_div.locator("li").all()
                            if bullets:
                                job.qualifications_asset_bullets = [b.inner_text().strip() for b in bullets]
                        elif "Equivalency" in heading_text:
                            job.qualifications_equivalency_text = content
                        elif "Benefits" in heading_text:
                            job.benefits_body = content
                            # Extract benefits link if present
                            link = content_div.locator("a").first
                            if link.count() > 0:
                                job.benefits_link_url = link.get_attribute("href")
                        elif "Working Conditions" in heading_text:
                            job.working_conditions_body = content
                        elif "Additional Information" in heading_text:
                            job.additional_information_body = content
                        elif "What We Offer" in heading_text:
                            bullets = content_div.locator("li").all()
                            if bullets:
                                job.what_we_offer_bullets = [b.inner_text().strip() for b in bullets]
                            else:
                                job.what_we_offer_bullets = [content]
                        elif "Employment Equity" in heading_text:
                            job.employment_equity_body = content
                        elif "Accommodation" in heading_text:
                            job.accommodation_body = content
                    
                    except Exception as e:
                        logger.warning(f"  ⚠ Error parsing section: {e}")
                        continue
                
                # Extract Employment Equity and Accommodation statements (they're outside section divs)
                try:
                    full_text = description_span.inner_text()
                    
                    # Employment Equity Statement
                    eq_match = re.search(r'Employment Equity Statement:?\s*(.+?)(?=Accommodation Statement:|$)', full_text, re.DOTALL | re.IGNORECASE)
                    if eq_match:
                        job.employment_equity_body = eq_match.group(1).strip()
                    
                    # Accommodation Statement
                    acc_match = re.search(r'Accommodation Statement:?\s*(.+?)(?=This is a bargaining|$)', full_text, re.DOTALL | re.IGNORECASE)
                    if acc_match:
                        job.accommodation_body = acc_match.group(1).strip()
                
                except Exception as e:
                    logger.warning(f"  ⚠ Error extracting statements: {e}")
        
        except Exception as e:
            logger.warning(f"  ⚠ Error extracting content sections: {e}")
        
        logger.info(f"  ✓ Successfully parsed job {job_id}")
        return job
        
    except Exception as e:
        logger.error(f"  ✗ Error parsing job page: {e}")
        return None


def save_job_to_json(job: NSJob) -> None:
    """
    Save job data to JSON file.
    
    Args:
        job: NSJob object to save
    """
    try:
        json_file = JOBS_JSON_DIR / f"ns_job_{job.job_id}.json"
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"  💾 Saved JSON: {json_file.name}")
        
    except Exception as e:
        logger.error(f"  ✗ Error saving job to JSON: {e}")


def scrape_keyword(page: Page, keyword: str, keywords: List[str]) -> List[NSJob]:
    """
    Scrape all jobs for a specific keyword.
    
    Args:
        page: Playwright page object
        keyword: Keyword to search for
        keywords: Full list of keywords for matching
    
    Returns:
        List of NSJob objects
    """
    jobs = []
    
    try:
        # Perform search
        search_url = search_jobs(page, keyword)
        
        # Save search results HTML
        search_html_file = SEARCH_HTML_DIR / f"ns_search_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(search_html_file, "w", encoding="utf-8") as f:
            f.write(page.content())
        logger.debug(f"💾 Saved search HTML: {search_html_file.name}")
        
        # Get total pages
        total_pages = get_total_pages(page)
        logger.info(f"📄 Total pages for '{keyword}': {total_pages}")
        
        # Extract jobs from all pages
        all_job_links = []
        
        for page_num in range(1, total_pages + 1):
            logger.info(f"📄 Processing page {page_num}/{total_pages}")
            
            if page_num > 1:
                navigate_to_page(page, keyword, page_num)
            
            # Extract job links from current page (ALL jobs, not filtered)
            page_jobs = extract_job_links(page, keyword, keywords)
            all_job_links.extend(page_jobs)
            
            logger.info(f"✓ Page {page_num}/{total_pages}: Found {len(page_jobs)} matching jobs")
        
        logger.info(f"✓ Total matching jobs for '{keyword}': {len(all_job_links)}")
        
        # Scrape each job
        scraped_count = 0
        skipped_count = 0
        
        for i, (job_url, job_title, matched_kw, match_score) in enumerate(all_job_links, 1):
            # Extract job ID to check for duplicates
            job_id = extract_job_id_from_url(job_url)
            
            if job_id:
                # Check if job already exists
                json_file = JOBS_JSON_DIR / f"ns_job_{job_id}.json"
                if json_file.exists():
                    logger.info(f"⏭️  [{i}/{len(all_job_links)}] Skipping duplicate job {job_id}: {job_title}")
                    skipped_count += 1
                    continue
            
            logger.info(f"📋 [{i}/{len(all_job_links)}] Scraping: {job_title}")
            
            try:
                job = parse_job_page(page, job_url, job_title, keyword, matched_kw, match_score)
                
                if job:
                    save_job_to_json(job)
                    jobs.append(job)
                    scraped_count += 1
                    logger.info(f"✓ [{i}/{len(all_job_links)}] Successfully scraped job {job.job_id}")
                else:
                    logger.warning(f"⚠ [{i}/{len(all_job_links)}] Failed to parse job")
            
            except Exception as e:
                logger.error(f"✗ [{i}/{len(all_job_links)}] Error scraping job: {e}")
            
            # Delay between jobs
            time.sleep(random.uniform(2.0, 4.0))
        
        logger.info(f"✓ Completed keyword '{keyword}': {scraped_count} jobs scraped, {skipped_count} duplicates skipped")
        
    except Exception as e:
        logger.error(f"✗ Error scraping keyword '{keyword}': {e}")
    
    return jobs


def main():
    """
    Main scraper function.
    """
    logger.info("=" * 80)
    logger.info("Nova Scotia Government Job Scraper")
    logger.info("=" * 80)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Headless mode: {HEADLESS}")
    logger.info("=" * 80)
    
    # Load keywords
    keywords = load_keywords()
    
    if not keywords:
        logger.error("✗ No keywords loaded. Exiting.")
        return
    
    logger.info(f"🔍 Searching for {len(keywords)} keywords")
    logger.info("=" * 80)
    
    all_jobs = []
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(TIMEOUT)
        
        try:
            # Process each keyword
            for i, keyword in enumerate(keywords, 1):
                logger.info("=" * 80)
                logger.info(f"Keyword {i}/{len(keywords)}: {keyword}")
                logger.info("=" * 80)
                
                jobs = scrape_keyword(page, keyword, keywords)
                all_jobs.extend(jobs)
                
                # Delay between keywords
                if i < len(keywords):
                    delay = DELAY_BETWEEN_SEARCHES
                    logger.info(f"⏱ Waiting {delay}s before next keyword...")
                    time.sleep(delay)
        
        finally:
            # Close browser
            browser.close()
    
    # Summary
    logger.info("=" * 80)
    logger.info("Scraping Complete")
    logger.info("=" * 80)
    logger.info(f"Total keywords searched: {len(keywords)}")
    logger.info(f"New jobs scraped this run: {len(all_jobs)}")
    
    # Count total unique jobs saved
    total_json_files = len(list(JOBS_JSON_DIR.glob("ns_job_*.json")))
    logger.info(f"Total unique jobs in database: {total_json_files}")
    
    logger.info(f"JSON files saved: {JOBS_JSON_DIR}")
    logger.info(f"HTML files saved: {JOBS_HTML_DIR}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 80)
    logger.info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
