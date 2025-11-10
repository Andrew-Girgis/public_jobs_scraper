"""
Ontario (ONT) Public Service Job Scraper

This scraper searches through all job postings on https://www.gojobs.gov.on.ca/Search.aspx
and matches them against keywords from list-of-jobs.txt using fuzzy matching.

Architecture:
1. Load job keywords from list-of-jobs.txt
2. Iterate through all pages on the search results
3. For each job listing, perform fuzzy matching against keywords
4. Save matching job links
5. Visit each matched job and extract full details
6. Save job data as JSON

Can be run standalone or imported into a batch scraper.
"""

import json
import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from urllib.parse import urljoin, parse_qs, urlparse

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from rapidfuzz import fuzz, process

from src.ONT.config import (
    BASE_URL,
    SEARCH_URL,
    JOBS_JSON_DIR,
    JOBS_HTML_DIR,
    SEARCH_HTML_DIR,
    LOG_DIR,
    JOB_LIST_FILE,
    HEADLESS,
    TIMEOUT,
    DELAY_BETWEEN_PAGES,
    FUZZY_MATCH_THRESHOLD,
)
from src.ONT.models import OntJob, JobMatch

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / f"ont_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_job_keywords() -> List[str]:
    """
    Load job keywords from the list-of-jobs.txt file.
    
    Returns:
        List of job keywords to search for
    """
    try:
        with open(JOB_LIST_FILE, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(keywords)} job keywords from {JOB_LIST_FILE}")
        return keywords
    except FileNotFoundError:
        logger.error(f"Job list file not found: {JOB_LIST_FILE}")
        return []


def fuzzy_match_title(job_title: str, keywords: List[str], threshold: int = FUZZY_MATCH_THRESHOLD) -> Optional[Tuple[str, float]]:
    """
    Perform smart token-based matching of job title against list of keywords.
    Uses exact phrase matching and token combination matching instead of fuzzy scoring.
    
    Args:
        job_title: The job title to match
        keywords: List of keywords/phrases to match against
        threshold: Unused (kept for compatibility)
    
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
        ({"research", "analyst"}, "Research Analyst"),
        ({"project", "manager"}, "Project Manager"),
        ({"senior", "manager"}, "Senior Manager"),
    ]
    
    for required_tokens, pattern_name in special_patterns:
        if required_tokens.issubset(title_tokens):
            logger.debug(f"Pattern match: '{job_title}' matches pattern '{pattern_name}' (score: 85)")
            return pattern_name, 85.0
    
    return None


def extract_job_id_from_url(url: str) -> Optional[str]:
    """
    Extract job ID from Ontario job URL.
    
    Args:
        url: The job URL
    
    Returns:
        Job ID if found, None otherwise
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    job_id = params.get('JobID', [None])[0]
    return job_id


def human_like_scroll(page: Page, steps: int = 5) -> None:
    """
    Scroll through the page in a human-like manner.
    
    Args:
        page: Playwright page object
        steps: Number of scroll steps (default: 5)
    """
    try:
        # Get page height
        page_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        
        logger.info(f"  📜 Scrolling page (height: {page_height}px, viewport: {viewport_height}px)")
        
        # Scroll down in steps
        for i in range(steps):
            # Random scroll distance (30-70% of viewport)
            scroll_amount = int(viewport_height * random.uniform(0.3, 0.7))
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            
            pause = random.uniform(0.3, 0.8)
            logger.info(f"  ↓ Scroll step {i+1}/{steps}: {scroll_amount}px, pause {pause:.2f}s")
            
            # Random pause between scrolls (0.3-0.8 seconds)
            time.sleep(pause)
        
        # Scroll back to top smoothly
        logger.info(f"  ↑ Scrolling back to top...")
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(random.uniform(0.2, 0.5))
        
    except Exception as e:
        logger.warning(f"Error during human-like scrolling: {e}")


def get_total_pages(page: Page) -> int:
    """
    Get the total number of search result pages.
    
    Args:
        page: Playwright page object
    
    Returns:
        Total number of pages
    """
    try:
        # Look for pagination elements in the #pager div
        pager = page.locator('#pager .ontario-pagination')
        
        if pager.count() > 0:
            # Get all page links
            page_links = pager.locator('a[title*="Result Page"]').all()
            page_numbers = []
            
            for link in page_links:
                # Extract page number from title attribute
                # Title format: "Result Page 14"
                title = link.get_attribute('title')
                if title:
                    match = re.search(r'Result Page (\d+)', title)
                    if match:
                        page_numbers.append(int(match.group(1)))
            
            if page_numbers:
                max_page = max(page_numbers)
                logger.info(f"Detected maximum page number: {max_page}")
                return max_page
        
        # Fallback: try the old method
        pagination = page.locator('.ontario-pagination').first
        if pagination.count() > 0:
            page_links = pagination.locator('a').all()
            page_numbers = []
            for link in page_links:
                text = link.inner_text().strip()
                if text.isdigit():
                    page_numbers.append(int(text))
            
            if page_numbers:
                return max(page_numbers)
        
        # If we can't find pagination, assume 1 page
        logger.warning("Could not detect pagination, assuming 1 page")
        return 1
    except Exception as e:
        logger.warning(f"Could not determine total pages: {e}")
        return 1


def scrape_search_page(page: Page, page_number: int, keywords: List[str]) -> List[JobMatch]:
    """
    Scrape a single search results page and find matching jobs.
    
    Args:
        page: Playwright page object
        page_number: Current page number
        keywords: List of keywords to match against
    
    Returns:
        List of JobMatch objects for matched jobs
    """
    logger.info(f"Scraping search page {page_number}")
    matches = []
    
    try:
        # Save the HTML for debugging
        html_content = page.content()
        html_file = SEARCH_HTML_DIR / f"search_page_{page_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.debug(f"Saved search page HTML to {html_file}")
        
        # Find all job links on the page
        # Job links have class "job-link" and href containing "Preview.aspx"
        # Example: <a id="ctl00_MainContent_rptSearchResult_ctl01_lnkJobTitleEN" class="job-link" href="/Preview.aspx?Language=English&JobID=236542">
        job_links = page.locator('a.job-link[href*="Preview.aspx"]').all()
        
        logger.info(f"Found {len(job_links)} job listings on page {page_number}")
        
        for idx, link in enumerate(job_links):
            try:
                # Extract job title
                job_title = link.inner_text().strip()
                
                # Log the job title being checked
                logger.info(f"Checking job {idx+1}/{len(job_links)}: '{job_title}'")
                
                # Extract job URL
                job_url = link.get_attribute('href')
                if not job_url:
                    continue
                    
                if not job_url.startswith('http'):
                    job_url = urljoin(BASE_URL, job_url)
                
                # Extract job ID from URL
                job_id = extract_job_id_from_url(job_url)
                if not job_id:
                    logger.warning(f"Could not extract job ID from URL: {job_url}")
                    continue
                
                # Perform fuzzy matching against keyword list
                match_result = fuzzy_match_title(job_title, keywords)
                if match_result:
                    matched_keyword, score = match_result
                    job_match = JobMatch(
                        job_id=job_id,
                        title=job_title,
                        url=job_url,
                        matched_keyword=matched_keyword,
                        match_score=score,
                        page_number=page_number
                    )
                    matches.append(job_match)
                    logger.info(f"✓ MATCH FOUND: '{job_title}' (ID: {job_id}) - Keyword: '{matched_keyword}' (Score: {score})")
                else:
                    logger.debug(f"  No match for '{job_title}'")
                
            except Exception as e:
                logger.error(f"Error processing job link {idx} on page {page_number}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error scraping search page {page_number}: {e}")
    
    return matches


def navigate_to_page(page: Page, page_number: int) -> bool:
    """
    Navigate to a specific page number in the search results.
    
    Args:
        page: Playwright page object
        page_number: Page number to navigate to
    
    Returns:
        True if navigation successful, False otherwise
    """
    try:
        if page_number == 1:
            # Already on first page after search
            return True
        
        # Human-like behavior: Scroll down to pagination area
        logger.info(f"Scrolling to page {page_number} link...")
        try:
            # Scroll to bottom where pagination is
            page.evaluate("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })")
            time.sleep(random.uniform(0.8, 1.5))
        except Exception as e:
            logger.warning(f"Error scrolling to pagination: {e}")
        
        # Look for page number link with specific pattern
        # Example: <a id="ctl00_MainContent_lnkButton_Page1" title="Result Page 2" href="javascript:__doPostBack(...)">2</a>
        # The page link shows the page number as text
        page_link = page.locator(f'#pager a[title*="Result Page {page_number}"]').first
        
        if page_link.count() == 0:
            # Try alternate selector - just text match
            page_link = page.locator(f'#pager a:text-is("{page_number}")').first
        
        if page_link.count() > 0:
            logger.info(f"Clicking pagination link for page {page_number}")
            page_link.scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.7))
            page_link.click()
            
            # Wait for the page to update
            page.wait_for_load_state("networkidle", timeout=TIMEOUT)
            time.sleep(random.uniform(2.0, 3.5))  # Random wait for JavaScript to populate results
            
            return True
        else:
            logger.warning(f"Could not find link for page {page_number}")
            return False
        
    except Exception as e:
        logger.error(f"Error navigating to page {page_number}: {e}")
        return False


def parse_job_page(page: Page, job_match: JobMatch) -> Optional[OntJob]:
    """
    Parse a single Ontario job posting page and extract all details.
    
    Args:
        page: Playwright page object
        job_match: JobMatch object with basic job info
    
    Returns:
        OntJob object if successful, None otherwise
    """
    logger.info(f"Parsing job: {job_match.title} (ID: {job_match.job_id})")
    
    try:
        # Navigate to job page
        page.goto(job_match.url, timeout=TIMEOUT, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        
        # Save HTML for debugging
        html_content = page.content()
        html_file = JOBS_HTML_DIR / f"job_{job_match.job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.debug(f"Saved job HTML to {html_file}")
        
        # Extract title
        title_elem = page.locator('h1').first
        title = title_elem.inner_text().strip() if title_elem.count() > 0 else job_match.title
        
        # Helper function to extract field value
        def get_field_value(label: str) -> Optional[str]:
            """Extract value for a given label."""
            try:
                # Find the row containing the label
                row = page.locator(f'.ontario-row:has(strong:text-is("{label}"))').first
                if row.count() > 0:
                    # Get the value column
                    value_col = row.locator('.ontario-column').nth(1)
                    if value_col.count() > 0:
                        return value_col.inner_text().strip()
            except:
                pass
            return None
        
        # Extract basic fields
        organization = get_field_value("Organization:")
        division = get_field_value("Division:")
        city = get_field_value("City:")
        posting_status = get_field_value("Posting status:")
        position_language = get_field_value("Position(s) language:")
        job_term = get_field_value("Job term:")
        job_code = get_field_value("Job code:")
        salary_raw = get_field_value("Salary:")
        compensation_group = get_field_value("Compensation group:")
        work_hours = get_field_value("Work hours:")
        category = get_field_value("Category:")
        position_details = get_field_value("Position details:")
        
        # Parse salary
        salary_min = None
        salary_max = None
        salary_period = None
        if salary_raw:
            # Format: "$1,512.75  - $1,933.38 Per week*"
            salary_match = re.search(r'\$?([\d,]+\.?\d*)\s*-\s*\$?([\d,]+\.?\d*)\s*Per\s+(\w+)', salary_raw, re.IGNORECASE)
            if salary_match:
                try:
                    salary_min = float(salary_match.group(1).replace(',', ''))
                    salary_max = float(salary_match.group(2).replace(',', ''))
                    salary_period = salary_match.group(3).lower()
                except ValueError:
                    pass
        
        # Parse dates
        def parse_date(date_str: Optional[str]) -> Optional[datetime]:
            """Parse date string to datetime object."""
            if not date_str:
                return None
            try:
                # Format: "Friday, November 21, 2025 11:59 pm EST"
                # Try with time
                for fmt in [
                    "%A, %B %d, %Y %I:%M %p %Z",
                    "%A, %B %d, %Y %I:%M %p",
                    "%A, %B %d, %Y",
                    "%B %d, %Y",
                    "%Y-%m-%d"
                ]:
                    try:
                        return datetime.strptime(date_str.strip(), fmt)
                    except ValueError:
                        continue
            except:
                pass
            return None
        
        apply_by_str = get_field_value("Apply by:")
        apply_by = parse_date(apply_by_str)
        
        posted_on_str = get_field_value("Posted on:")
        posted_on = parse_date(posted_on_str)
        
        # Extract note
        note_elem = page.locator('.ontario-row:has(strong:text-is("Note:"))').first
        note = None
        if note_elem.count() > 0:
            note_content = note_elem.locator('ul, p').first
            if note_content.count() > 0:
                note = note_content.inner_text().strip()
        
        # Extract main content sections
        # The job page has all content in a single div with <hr> and <h2> tags separating sections
        about_the_job = None
        what_you_bring = None
        mandatory_requirements = None
        additional_info = None
        how_to_apply = None
        
        try:
            # Get all the main content divs and find the one with job content
            main_content_locators = page.locator('.ontario-row .ontario-columns.ontario-medium-12').all()
            
            main_html = None
            # Look for the div that contains "About the job"
            for locator in main_content_locators:
                html = locator.inner_html()
                if 'About the job' in html:
                    main_html = html
                    break
            
            if main_html:
                # Extract "About the job" section
                about_match = re.search(
                    r'<h2><strong>About the job</strong></h2>(.*?)(?:<hr>|<h2>|$)',
                    main_html,
                    re.DOTALL | re.IGNORECASE
                )
                if about_match:
                    # Strip HTML tags and clean up
                    about_the_job = re.sub(r'<br\s*/?>', '\n', about_match.group(1))
                    about_the_job = re.sub(r'<[^>]+>', '', about_the_job).strip()
                
                # Extract "What you bring to the team" section
                what_match = re.search(
                    r'<h2><strong>What you bring to the team</strong></h2>(.*?)(?:<hr>|<h2><strong>(?:Don\'t meet|How we support|What we offer|Additional information)</strong></h2>|$)',
                    main_html,
                    re.DOTALL | re.IGNORECASE
                )
                if what_match:
                    # Strip HTML tags but keep structure
                    what_you_bring = re.sub(r'<br\s*/?>', '\n', what_match.group(1))
                    # Keep h3 structure
                    what_you_bring = re.sub(r'<h3><strong>(.*?)</strong></h3>', r'\n\n\1:\n', what_you_bring)
                    what_you_bring = re.sub(r'<[^>]+>', '', what_you_bring).strip()
                
                # Extract "Additional information" section (if exists)
                additional_match = re.search(
                    r'<h2><strong>Additional information:?</strong></h2>(.*?)(?:<hr>|<h2>|$)',
                    main_html,
                    re.DOTALL | re.IGNORECASE
                )
                if additional_match:
                    additional_info = re.sub(r'<br\s*/?>', '\n', additional_match.group(1))
                    additional_info = re.sub(r'<[^>]+>', '', additional_info).strip()
                
        except Exception as e:
            logger.warning(f"Error extracting main content sections: {e}")
        
        # Extract "How to apply" section - this is usually at the bottom
        try:
            how_to_apply_elem = page.locator('text="How to apply"').first
            if how_to_apply_elem.count() > 0:
                # Get the parent section
                parent = how_to_apply_elem.locator('xpath=ancestor::div[contains(@class, "ontario-row")]').first
                if parent.count() > 0:
                    how_to_apply = parent.inner_text().strip()
        except Exception as e:
            logger.warning(f"Error extracting 'How to apply' section: {e}")
        
        # Create OntJob object
        ont_job = OntJob(
            job_id=job_match.job_id,
            url=job_match.url,
            title=title,
            organization=organization,
            division=division,
            city=city,
            posting_status=posting_status,
            position_language=position_language,
            job_term=job_term,
            job_code=job_code,
            salary=salary_raw,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_period=salary_period,
            apply_by=apply_by,
            posted_on=posted_on,
            position_details=position_details,
            compensation_group=compensation_group,
            work_hours=work_hours,
            category=category,
            note=note,
            about_the_job=about_the_job,
            what_you_bring=what_you_bring,
            mandatory_requirements=mandatory_requirements,
            additional_info=additional_info,
            how_to_apply=how_to_apply,
            scraped_at=datetime.now(),
            matched_keyword=job_match.matched_keyword,
            match_score=job_match.match_score
        )
        
        logger.info(f"✓ Successfully parsed job {job_match.job_id}")
        return ont_job
        
    except Exception as e:
        logger.error(f"Error parsing job {job_match.job_id}: {e}")
        return None


def save_job_json(job: OntJob) -> bool:
    """
    Save OntJob object to JSON file.
    
    Args:
        job: OntJob object to save
    
    Returns:
        True if successful, False otherwise
    """
    try:
        json_file = JOBS_JSON_DIR / f"ont_job_{job.job_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved job JSON to {json_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving job JSON for {job.job_id}: {e}")
        return False


def handle_captcha(page: Page) -> bool:
    """
    Detect if CAPTCHA is present and pause for manual solving.
    
    Args:
        page: Playwright page object
    
    Returns:
        True if CAPTCHA was solved (or not present), False otherwise
    """
    try:
        # Check for common CAPTCHA indicators
        captcha_selectors = [
            'iframe[src*="captcha"]',
            'iframe[src*="hcaptcha"]',
            'iframe[src*="recaptcha"]',
            '[class*="captcha"]',
            '[id*="captcha"]',
            'iframe[title*="captcha" i]',
            'form:has-text("CAPTCHA")',
        ]
        
        captcha_detected = False
        for selector in captcha_selectors:
            if page.locator(selector).count() > 0:
                captcha_detected = True
                break
        
        # Also check page text content
        page_text = page.content().lower()
        if 'captcha' in page_text or 'radware' in page_text:
            captcha_detected = True
        
        if captcha_detected:
            logger.warning("=" * 80)
            logger.warning("🤖 CAPTCHA DETECTED!")
            logger.warning("=" * 80)
            logger.warning("The Ontario job site has bot protection (Radware + hCaptcha).")
            logger.warning("Please solve the CAPTCHA in the browser window.")
            logger.warning("")
            logger.warning("The scraper will wait for 3 minutes...")
            logger.warning("Press ENTER in this terminal once you've solved it.")
            logger.warning("=" * 80)
            
            # Wait for user input or timeout (3 minutes)
            import sys
            import select
            
            if sys.platform != 'win32':
                # Unix-like systems (macOS, Linux)
                i, o, e = select.select([sys.stdin], [], [], 180)  # 3 minute timeout
                if i:
                    sys.stdin.readline()
                else:
                    logger.warning("Timeout waiting for CAPTCHA solution.")
                    return False
            else:
                # Windows - just wait for input
                try:
                    input("Press ENTER after solving CAPTCHA...")
                except KeyboardInterrupt:
                    return False
            
            logger.info("Continuing after CAPTCHA...")
            time.sleep(2)  # Brief pause after solving
            page.wait_for_load_state("networkidle", timeout=TIMEOUT)
            return True
        
        # No CAPTCHA detected
        return True
        
    except Exception as e:
        logger.error(f"Error handling CAPTCHA: {e}")
        return False


def scrape_all_jobs(page: Page) -> List[OntJob]:
    """
    Main scraping workflow: search all pages, match jobs, and extract details.
    
    Args:
        page: Playwright page object
    
    Returns:
        List of OntJob objects
    """
    logger.info("Starting Ontario job scraping workflow")
    
    # Load keywords
    keywords = load_job_keywords()
    if not keywords:
        logger.error("No keywords loaded. Exiting.")
        return []
    
    # Navigate to search page
    logger.info(f"Navigating to {SEARCH_URL}")
    page.goto(SEARCH_URL, timeout=TIMEOUT, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    
    # Handle CAPTCHA if present
    if not handle_captcha(page):
        logger.error("CAPTCHA handling failed or timed out. Exiting.")
        return []
    
    # Human-like behavior: Scroll down the page slowly
    logger.info("Scrolling page like a human")
    try:
        # Get page height
        page_height = page.evaluate("document.body.scrollHeight")
        # Scroll in chunks to simulate human behavior
        scroll_steps = 5
        for step in range(scroll_steps):
            scroll_position = (page_height / scroll_steps) * (step + 1)
            page.evaluate(f"window.scrollTo({{ top: {scroll_position}, behavior: 'smooth' }})")
            time.sleep(0.3 + (0.2 * (step % 2)))  # Variable delay
        logger.info("Page scrolled successfully")
    except Exception as e:
        logger.warning(f"Error during scrolling: {e}")
    
    # Select filter options before clicking Search
    # The Ontario site requires at least one filter to be selected for results to appear
    logger.info("Selecting search filters")
    try:
        # Scroll to the category dropdown first
        category_toggle = page.locator('button#multiselectToggle_ucCategory')
        if category_toggle.count() > 0:
            # Scroll element into view smoothly
            category_toggle.scroll_into_view_if_needed()
            time.sleep(0.5)
            
            # Human-like mouse movement and click
            category_toggle.click()
            logger.info("Opened job category dropdown")
            time.sleep(1)  # Brief wait for dropdown to open
        
        # Select "All job categories" checkbox using its specific ID
        all_categories_checkbox = page.locator('input#chkOption-ucCategory-0[type="checkbox"]')
        
        if all_categories_checkbox.count() > 0:
            # Scroll to checkbox and click
            all_categories_checkbox.scroll_into_view_if_needed()
            time.sleep(0.3)
            all_categories_checkbox.check()
            logger.info("✓ Selected 'All job categories' checkbox")
            time.sleep(0.5)  # Brief wait for selection to register
            
            # Verify the checkbox is actually checked
            is_checked = all_categories_checkbox.is_checked()
            logger.info(f"Checkbox checked state: {is_checked}")
            
            # Close the dropdown by clicking the toggle button again
            if category_toggle.count() > 0:
                category_toggle.scroll_into_view_if_needed()
                time.sleep(0.3)
                category_toggle.click()
                logger.info("Closed job category dropdown")
                time.sleep(0.5)
        else:
            logger.warning("Could not find 'All job categories' checkbox - attempting search anyway")
    except Exception as e:
        logger.error(f"Error selecting filter: {e}")
        logger.info("Attempting to search without filter selection...")
    
    # Human-like behavior: Scroll to the Search button
    logger.info("Scrolling to Search button")
    try:
        search_button = page.locator('input[type="submit"][value="Search"]')
        search_button.scroll_into_view_if_needed()
        time.sleep(0.8)  # Pause like a human reading the page
        logger.info("Search button is now in view")
    except Exception as e:
        logger.warning(f"Error scrolling to search button: {e}")
    
    # Take a screenshot before clicking Search to verify UI state
    try:
        screenshot_path = SEARCH_HTML_DIR / f"before_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_path))
        logger.info(f"Saved screenshot before search: {screenshot_path}")
    except Exception as e:
        logger.warning(f"Could not save screenshot: {e}")
    
    # Click the Search button to submit the form and get results
    logger.info("Clicking Search button to load job results")
    try:
        search_button = page.locator('input[type="submit"][value="Search"]')
        search_button.click()
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        logger.info("Search submitted successfully")
        
        # Wait for results to load - the page needs time for JavaScript to populate results
        logger.info("Waiting for search results to load...")
        time.sleep(8)  # Increased from 5 to 8 seconds to avoid bot detection
        
        # Wait for the SearchResultDiv to have content or for a reasonable timeout
        try:
            # Wait for either job listings to appear or pagination to appear (indicates results loaded)
            page.wait_for_selector('#SearchResultDiv table, #pager a', timeout=15000)
            logger.info("Search results loaded successfully")
        except Exception as e:
            logger.warning(f"Timeout waiting for results, but continuing anyway: {e}")
        
        # Take another screenshot after search to see results
        try:
            screenshot_path = SEARCH_HTML_DIR / f"after_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=str(screenshot_path))
            logger.info(f"Saved screenshot after search: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Could not save after-search screenshot: {e}")
            
    except Exception as e:
        logger.error(f"Error clicking search button: {e}")
        return []
    
    # Get total pages
    total_pages = 14  # Ontario job site has 14 pages
    logger.info(f"Total pages to scrape: {total_pages}")
    
    # Collect all matches across all pages
    all_matches: List[JobMatch] = []
    
    for page_num in range(1, total_pages + 1):
        logger.info(f"Processing page {page_num}/{total_pages}")
        
        # Navigate to page
        if not navigate_to_page(page, page_num):
            logger.warning(f"Skipping page {page_num} due to navigation error")
            continue
        
        # Scrape page and collect matches
        matches = scrape_search_page(page, page_num, keywords)
        all_matches.extend(matches)
        
        logger.info(f"Found {len(matches)} matches on page {page_num}")
        
        # Delay between pages
        if page_num < total_pages:
            time.sleep(DELAY_BETWEEN_PAGES)
    
    logger.info(f"Total matches found: {len(all_matches)}")
    
    # Now visit each matched job and extract full details
    jobs: List[OntJob] = []
    
    for idx, job_match in enumerate(all_matches, 1):
        logger.info(f"Processing job {idx}/{len(all_matches)}: {job_match.title}")
        
        # Parse job page
        job = parse_job_page(page, job_match)
        
        if job:
            jobs.append(job)
            # Save to JSON
            save_job_json(job)
        
        # Delay between job page requests
        if idx < len(all_matches):
            time.sleep(DELAY_BETWEEN_PAGES)
    
    logger.info(f"Successfully scraped {len(jobs)} jobs")
    return jobs


def main():
    """
    Main entry point for the Ontario job scraper.
    Can be run standalone or imported by batch scraper.
    """
    logger.info("=" * 80)
    logger.info("Ontario (ONT) Job Scraper Starting")
    logger.info("=" * 80)
    
    with sync_playwright() as p:
        # Launch browser with stealth options
        logger.info(f"Launching Chromium browser (headless={HEADLESS})")
        browser: Browser = p.chromium.launch(
            headless=HEADLESS,
            args=[
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        # Create context with realistic user agent and settings
        context: BrowserContext = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-CA',
            timezone_id='America/Toronto',
            extra_http_headers={
                'Accept-Language': 'en-CA,en-US;q=0.9,en;q=0.8',
            }
        )
        
        # Add extra stealth measures
        context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-CA', 'en-US', 'en']
            });
            
            // Mock chrome object
            window.chrome = {
                runtime: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        page: Page = context.new_page()
        
        try:
            # Run the scraping workflow
            jobs = scrape_all_jobs(page)
            
            logger.info(f"Scraping complete. Total jobs scraped: {len(jobs)}")
            
        finally:
            # Clean up
            logger.info("Closing browser")
            context.close()
            browser.close()
    
    logger.info("Ontario Job Scraper finished")


if __name__ == "__main__":
    main()
