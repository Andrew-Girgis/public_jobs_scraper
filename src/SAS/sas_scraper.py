"""
Saskatchewan (SAS) Government Job Scraper - Taleo System

This scraper extracts job postings from the Saskatchewan government job board
(govskpsc.taleo.net) using keyword search and token-based matching.
"""

import json
import logging
import os
import re
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from SAS.config import (
    BASE_URL,
    SEARCH_URL,
    JOB_DETAIL_URL,
    DATA_DIR,
    JOBS_JSON_DIR,
    JOBS_HTML_DIR,
    SEARCH_HTML_DIR,
    LOG_DIR,
    JOB_LIST_FILE,
    HEADLESS,
    TIMEOUT,
    DELAY_BETWEEN_PAGES,
    DELAY_BETWEEN_SEARCHES
)
from SAS.models import SASJob

# Set up logging
log_file = LOG_DIR / f"sas_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
        List of keywords to search for
    """
    try:
        with open(JOB_LIST_FILE, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        logger.info(f"✓ Loaded {len(keywords)} keywords from {JOB_LIST_FILE.name}")
        return keywords
    except Exception as e:
        logger.error(f"✗ Error loading keywords: {e}")
        return []


def token_match_title(job_title: str, keywords: List[str]) -> Tuple[Optional[str], float]:
    """
    Match job title against keywords using token-based matching.
    Similar to NS scraper's 5-tier matching system.
    
    Args:
        job_title: Job title to match
        keywords: List of keywords to match against
    
    Returns:
        Tuple of (matched_keyword, match_score) or (None, 0.0)
    """
    job_title_lower = job_title.lower()
    job_tokens = set(re.findall(r'\b\w+\b', job_title_lower))
    
    # Word variations for better matching
    word_variations = {
        'economist': ['economic', 'economy', 'economics'],
        'analyst': ['analysis', 'analytical'],
        'manager': ['management', 'managing'],
        'developer': ['development', 'developing'],
        'administrator': ['administration', 'administrative'],
        'coordinator': ['coordination', 'coordinating'],
        'officer': ['official'],
        'advisor': ['advisory', 'advising'],
        'director': ['directorate'],
        'specialist': ['specialization'],
        'consultant': ['consulting', 'consultancy']
    }
    
    best_match = None
    best_score = 0.0
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        keyword_tokens = set(re.findall(r'\b\w+\b', keyword_lower))
        
        # Tier 1: Exact phrase match (substring) - 100 points
        if keyword_lower in job_title_lower:
            if 100 > best_score:
                best_match = keyword
                best_score = 100
                continue
        
        # Tier 2: All keyword tokens present - 95 points
        if keyword_tokens and keyword_tokens.issubset(job_tokens):
            if 95 > best_score:
                best_match = keyword
                best_score = 95
                continue
        
        # Tier 3: Any keyword token present - 90 points
        if keyword_tokens and keyword_tokens.intersection(job_tokens):
            if 90 > best_score:
                best_match = keyword
                best_score = 90
                continue
        
        # Tier 4: Word variations match - 88 points
        for token in keyword_tokens:
            if token in word_variations:
                variations = set(word_variations[token])
                if variations.intersection(job_tokens):
                    if 88 > best_score:
                        best_match = keyword
                        best_score = 88
                        break
        
        # Tier 5: Common role patterns - 85 points
        role_patterns = [
            (r'\binformation\s+management\b', 'information management'),
            (r'\bproject\s+management\b', 'project management'),
            (r'\bdata\s+analysis\b', 'data analysis')
        ]
        
        for pattern, role in role_patterns:
            if re.search(pattern, job_title_lower) and role in keyword_lower:
                if 85 > best_score:
                    best_match = keyword
                    best_score = 85
                    break
    
    return (best_match, best_score) if best_score > 0 else (None, 0.0)


def extract_job_id_from_url(url: str) -> Optional[str]:
    """
    Extract job ID from Saskatchewan job URL.
    Example: jobdetail.ftl?job=12345 -> 12345
    
    Args:
        url: The job URL
    
    Returns:
        Job ID if found, None otherwise
    """
    match = re.search(r'job=(\d+)', url)
    if match:
        return match.group(1)
    return None


def human_like_scroll(page: Page, steps: int = 3) -> None:
    """
    Scroll through the page in a human-like manner.
    
    Args:
        page: Playwright page object
        steps: Number of scroll steps
    """
    try:
        page_height = page.evaluate("document.body.scrollHeight")
        current_position = 0
        step_size = page_height // steps
        
        for _ in range(steps):
            current_position += step_size + random.randint(-50, 50)
            page.evaluate(f"window.scrollTo(0, {current_position})")
            time.sleep(random.uniform(0.3, 0.7))
        
        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(random.uniform(0.2, 0.5))
    except Exception as e:
        logger.debug(f"Scroll error: {e}")


def search_jobs(page: Page, keyword: str) -> str:
    """
    Perform job search for a specific keyword.
    
    Args:
        page: Playwright page object
        keyword: Keyword to search for
    
    Returns:
        Search URL
    """
    logger.info(f"🔍 Searching for: '{keyword}'")
    
    # Navigate to search page
    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=TIMEOUT)
    time.sleep(random.uniform(2, 3))
    
    try:
        # Use the correct Taleo basic search input
        search_box = page.locator("input#basicSearchInterface\\.keywordInput, input[name='keyword']").first
        search_box.wait_for(state="visible", timeout=10000)
        search_box.fill(keyword)
        time.sleep(random.uniform(0.5, 1.0))
        
        # Press Enter or click search button
        search_box.press("Enter")
        
        # Wait for results
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(random.uniform(2, 3))
        
    except Exception as e:
        logger.warning(f"  ⚠ Search interaction error: {e}")
    
    return page.url


def extract_job_links(page: Page, keyword: str, keywords: List[str]) -> List[Tuple[str, str, str, float]]:
    """
    Extract job links from search results and filter using token matching.
    
    Args:
        page: Playwright page object
        keyword: Search keyword
        keywords: Full list of keywords for matching
    
    Returns:
        List of tuples: (job_url, job_title, matched_keyword, match_score)
    """
    matching_jobs = []
    
    try:
        # Wait for job results to load (Taleo-specific)
        page.wait_for_selector("table#requisitionListInterface\\.listRequisition", timeout=10000)
        
        # Debug: Log page title and URL
        logger.debug(f"  Page title: {page.title()}")
        logger.debug(f"  Current URL: {page.url}")
        
        # Taleo stores jobs in table with id "requisitionListInterface.listRequisition"
        # Each job is in a <div class="iconcontentpanel"> with id=job_number
        job_divs = page.locator("div.iconcontentpanel[id]").all()
        
        logger.info(f"  📋 Found {len(job_divs)} jobs on this page")
        
        for job_div in job_divs:
            try:
                # Get job ID from div id attribute
                job_id = job_div.get_attribute("id")
                if not job_id or not job_id.isdigit():
                    continue
                
                # Taleo uses span.titlelink > a structure for job titles
                title_link = job_div.locator("span.titlelink a").first
                
                if title_link.count() == 0:
                    continue
                    
                job_title = title_link.inner_text().strip()
                
                if not job_title:
                    continue
                
                # Build proper job URL using the job ID from div
                job_url = f"{BASE_URL}/careersection/10180/jobdetail.ftl?job={job_id}&lang=en"
                
                # Token match the title
                matched_kw, match_score = token_match_title(job_title, keywords)
                
                if matched_kw and match_score > 0:
                    matching_jobs.append((job_url, job_title, matched_kw, match_score))
                    logger.info(f"  ✓ MATCH: '{job_title}' → '{matched_kw}' (score: {match_score})")
                else:
                    logger.debug(f"  ✗ No match: '{job_title}'")
                    
            except Exception as e:
                logger.debug(f"  Error extracting job: {e}")
                continue
        
        logger.info(f"  ✓ Extracted {len(matching_jobs)} matching jobs from page")
        
    except Exception as e:
        logger.error(f"  ✗ Error extracting job links: {e}")
    
    return matching_jobs


def parse_salary(salary_text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Parse salary range from text.
    Example: "$9,515-$12,367 Monthly" -> (9515.0, 12367.0, "Monthly")
    
    Args:
        salary_text: Raw salary text
    
    Returns:
        Tuple of (min, max, frequency)
    """
    try:
        # Remove $ and commas
        cleaned = salary_text.replace('$', '').replace(',', '')
        
        # Extract min and max
        match = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', cleaned)
        if match:
            min_sal = float(match.group(1))
            max_sal = float(match.group(2))
            
            # Extract frequency
            freq_match = re.search(r'(Monthly|Annual|Bi-Weekly|Weekly|Hourly)', salary_text, re.IGNORECASE)
            frequency = freq_match.group(1) if freq_match else None
            
            return (min_sal, max_sal, frequency)
    except Exception as e:
        logger.debug(f"Error parsing salary: {e}")
    
    return (None, None, None)


def parse_job_page(page: Page, job_url: str, job_title: str, search_keyword: str, 
                   matched_keyword: str, match_score: float) -> Optional[SASJob]:
    """
    Parse a single job posting page.
    
    Args:
        page: Playwright page object
        job_url: URL of the job posting
        job_title: Job title
        search_keyword: The keyword used in search
        matched_keyword: Matched keyword from token matching
        match_score: Match score
    
    Returns:
        SASJob object or None if parsing fails
    """
    try:
        logger.info(f"  📄 Parsing job: {job_title}")
        
        # Navigate to job page
        page.goto(job_url, wait_until="domcontentloaded", timeout=TIMEOUT)
        time.sleep(random.uniform(1.5, 2.5))
        
        # Wait for the main content to load
        page.wait_for_selector('div.editablesection', timeout=30000)
        
        # Scroll for human-like behavior
        human_like_scroll(page)
        
        # Extract job ID
        job_id = extract_job_id_from_url(job_url)
        
        # Get full page content
        full_content = page.content()
        
        # Parse with BeautifulSoup for easier extraction
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(full_content, 'html.parser')
        
        # Find the main job details section
        editable_section = soup.select_one('div.editablesection')
        if not editable_section:
            logger.error(f"Could not find job details section for {job_id}")
            return None
        
        # Helper function to extract field value by label
        def get_field_value(label_text: str) -> str:
            """Helper to extract field value by label"""
            for content_line in editable_section.select('div.contentlinepanel'):
                label = content_line.select_one('span.subtitle')
                if label and label_text.lower() in label.get_text(strip=True).lower():
                    value = content_line.select_one('span.text')
                    return value.get_text(strip=True) if value else ""
            return ""
        
        # Extract competition number
        contest_elem = editable_section.select_one('span[id*="reqContestNumberValue"]')
        competition_number = contest_elem.get_text(strip=True) if contest_elem else ""
        
        # Extract metadata fields
        employment_type = get_field_value("Employment Type")
        location = get_field_value("Location")
        ministry = get_field_value("Ministry")
        salary_range = get_field_value("Salary Range")
        salary_frequency = ""
        
        # Check if salary has frequency (Monthly/Hourly)
        salary_line = None
        for content_line in editable_section.select('div.contentlinepanel'):
            if "Salary Range" in content_line.get_text():
                salary_line = content_line
                break
        
        if salary_line:
            texts = [span.get_text(strip=True) for span in salary_line.select('span.text')]
            if len(texts) >= 2:
                salary_range = texts[0]
                salary_frequency = texts[1]
        
        salary_supplement = get_field_value("Salary Supplement")
        grade = get_field_value("Grade")
        hours_of_work = get_field_value("Hours of Work")
        number_of_openings = get_field_value("Number of Openings")
        closing_date_raw = get_field_value("Closing Date")
        
        # Parse salary
        salary_min, salary_max, _ = parse_salary(salary_range) if salary_range else (None, None, None)
        
        # Parse closing date
        closing_date = None
        if closing_date_raw:
            try:
                # Format: "Nov 21, 2025, 12:59:00 AM"
                closing_date = datetime.strptime(closing_date_raw, "%b %d, %Y, %I:%M:%S %p")
            except:
                logger.debug(f"Could not parse closing date: {closing_date_raw}")
        
        # Extract description content (the main job description)
        description_elem = editable_section.select_one('div[id*="ID1748"] span, div[id*="ID1751"] span')
        description_html = str(description_elem) if description_elem else ""
        
        # Parse the description into sections
        desc_soup = BeautifulSoup(description_html, 'html.parser')
        
        # Ministry description (first paragraph)
        ministry_desc = ""
        first_p = desc_soup.select_one('p')
        if first_p and "The Opportunity" not in first_p.get_text():
            ministry_desc = first_p.get_text(strip=True)
        
        # The Opportunity section
        opportunity = ""
        for p in desc_soup.select('p'):
            if "The Opportunity" in p.get_text():
                next_p = p.find_next_sibling('p')
                if next_p:
                    opportunity = next_p.get_text(strip=True)
                break
        
        # Helper function to extract bullet points from a section
        def extract_section_bullets(section_title: str) -> list:
            """Extract bullet points from a section"""
            bullets = []
            for strong in desc_soup.select('strong'):
                if section_title.lower() in strong.get_text().lower():
                    # Find the next <ul> after this heading
                    parent = strong.find_parent('p')
                    if parent:
                        ul = parent.find_next_sibling('ul')
                        if ul:
                            for li in ul.select('li'):
                                text = li.get_text(strip=True)
                                if text:
                                    bullets.append(text)
                    break
            return bullets
        
        # Extract responsibility sections
        strategic_leadership = extract_section_bullets("Strategic Leadership")
        technical_oversight = extract_section_bullets("Technical Oversight")
        information_mgmt = extract_section_bullets("Information") or extract_section_bullets("Knowledge Management")
        stakeholder_engagement = extract_section_bullets("Stakeholder Engagement")
        team_mgmt = extract_section_bullets("Team") or extract_section_bullets("Resource Management")
        
        # Combine all responsibilities
        all_responsibilities = (strategic_leadership + technical_oversight + 
                              information_mgmt + stakeholder_engagement + team_mgmt)
        responsibilities_text = "\n".join([f"- {item}" for item in all_responsibilities])
        
        # Extract qualifications
        ideal_candidate = extract_section_bullets("The Ideal Candidate") or extract_section_bullets("Ideal Candidate")
        
        # Extract education requirement
        education = ""
        for p in desc_soup.select('p'):
            text = p.get_text()
            if "post-graduate degree" in text.lower() or "typically" in text.lower():
                education = p.get_text(strip=True)
                break
        
        # What We Offer
        what_we_offer_bullets = extract_section_bullets("What We Offer")
        what_we_offer_text = "\n".join([f"- {item}" for item in what_we_offer_bullets])
        
        # Diversity statement
        diversity_elem = editable_section.select_one('div[id*="ID1764"] span, div[id*="ID1767"] span')
        diversity_statement = diversity_elem.get_text(strip=True) if diversity_elem else ""
        
        # Get full description text
        full_description = desc_soup.get_text(separator="\n", strip=True)
        
        # Create job object
        job = SASJob(
            job_id=job_id,
            url=job_url,
            job_title=job_title,
            employment_type=employment_type,
            location=location,
            ministry=ministry,
            salary_range=salary_range,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_frequency=salary_frequency,
            grade=grade,
            hours_of_work=hours_of_work,
            number_of_openings=int(number_of_openings) if number_of_openings and number_of_openings.isdigit() else None,
            closing_date=closing_date,
            ministry_description=ministry_desc,
            the_opportunity=opportunity,
            responsibilities=responsibilities_text,
            strategic_leadership_planning="\n".join([f"- {item}" for item in strategic_leadership]),
            technical_oversight="\n".join([f"- {item}" for item in technical_oversight]),
            information_knowledge_management="\n".join([f"- {item}" for item in information_mgmt]),
            stakeholder_engagement_collaboration="\n".join([f"- {item}" for item in stakeholder_engagement]),
            team_resource_management="\n".join([f"- {item}" for item in team_mgmt]),
            the_ideal_candidate="\n".join([f"- {item}" for item in ideal_candidate]),
            required_qualifications=ideal_candidate,
            education_requirements=education,
            what_we_offer=what_we_offer_text,
            benefits_list=what_we_offer_bullets,
            diversity_statement=diversity_statement,
            full_description=full_description,
            scraped_at=datetime.now(),
            search_keyword=search_keyword,
            matched_keyword=matched_keyword,
            match_score=match_score
        )
        
        # Save HTML
        try:
            html_file = JOBS_HTML_DIR / f"sas_job_{job_id}.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(full_content)
            logger.debug(f"  💾 Saved HTML: {html_file.name}")
        except Exception as e:
            logger.debug(f"  Error saving HTML: {e}")
        
        logger.info(f"  ✓ Successfully parsed job {job_id}")
        return job
        
    except Exception as e:
        logger.error(f"  ✗ Error parsing job page: {e}")
        return None


def save_job_to_json(job: SASJob) -> None:
    """
    Save job data to JSON file.
    
    Args:
        job: SASJob object to save
    """
    try:
        json_file = JOBS_JSON_DIR / f"sas_job_{job.job_id}.json"
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"  💾 Saved JSON: {json_file.name}")
        
    except Exception as e:
        logger.error(f"  ✗ Error saving job to JSON: {e}")


def scrape_keyword(page: Page, keyword: str, keywords: List[str]) -> List[SASJob]:
    """
    Scrape all jobs for a specific keyword.
    
    Args:
        page: Playwright page object
        keyword: Keyword to search for
        keywords: Full list of keywords for matching
    
    Returns:
        List of SASJob objects
    """
    jobs = []
    
    try:
        # Perform search
        search_url = search_jobs(page, keyword)
        
        # Save search results HTML and screenshot for debugging
        search_html_file = SEARCH_HTML_DIR / f"sas_search_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(search_html_file, "w", encoding="utf-8") as f:
            f.write(page.content())
        logger.debug(f"💾 Saved search HTML: {search_html_file.name}")
        
        # Take screenshot for debugging (first keyword only)
        try:
            screenshot_file = SEARCH_HTML_DIR / f"sas_search_{keyword.replace(' ', '_')}.png"
            page.screenshot(path=str(screenshot_file), full_page=True)
            logger.debug(f"📸 Saved screenshot: {screenshot_file.name}")
        except:
            pass
        
        # Extract job links with token matching
        job_links = extract_job_links(page, keyword, keywords)
        
        if len(job_links) == 0:
            logger.info(f"ℹ️  No matching jobs found for '{keyword}'")
        else:
            logger.info(f"✓ Found {len(job_links)} matching job{'s' if len(job_links) > 1 else ''} for '{keyword}'")
        
        # Scrape each job with duplicate checking
        scraped_count = 0
        skipped_count = 0
        
        for i, (job_url, job_title, matched_kw, match_score) in enumerate(job_links, 1):
            # Extract job ID to check for duplicates
            job_id = extract_job_id_from_url(job_url)
            
            if job_id:
                # Check if job already exists
                json_file = JOBS_JSON_DIR / f"sas_job_{job_id}.json"
                if json_file.exists():
                    logger.info(f"⏭️  [{i}/{len(job_links)}] Skipping duplicate job {job_id}: {job_title}")
                    skipped_count += 1
                    continue
            
            logger.info(f"📋 [{i}/{len(job_links)}] Scraping: {job_title}")
            
            try:
                job = parse_job_page(page, job_url, job_title, keyword, matched_kw, match_score)
                
                if job:
                    save_job_to_json(job)
                    jobs.append(job)
                    scraped_count += 1
                    logger.info(f"✓ [{i}/{len(job_links)}] Successfully scraped job {job.job_id}")
                else:
                    logger.warning(f"⚠ [{i}/{len(job_links)}] Failed to parse job")
            
            except Exception as e:
                logger.error(f"✗ [{i}/{len(job_links)}] Error scraping job: {e}")
            
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
    logger.info("Saskatchewan Government Job Scraper")
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
    total_json_files = len(list(JOBS_JSON_DIR.glob("sas_job_*.json")))
    logger.info(f"Total unique jobs in database: {total_json_files}")
    
    logger.info(f"JSON files saved: {JOBS_JSON_DIR}")
    logger.info(f"HTML files saved: {JOBS_HTML_DIR}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 80)
    logger.info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
