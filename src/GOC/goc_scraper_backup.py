"""
Government of Canada (GOC) Job Scraper

Scrapes job postings from the Government of Canada job portal using Playwright.
Reads job title queries from list-of-jobs.txt, searches for each query,
paginates through results, and extracts detailed job information.

This is a synchronous, single-threaded implementation designed for simplicity
and reliability. All data is saved locally as HTML and JSON files.
"""

import logging
import re
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from logging.handlers import RotatingFileHandler

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging() -> logging.Logger:
    """
    Configure logging to write to both console and rotating file.
    
    Returns:
        Logger instance configured for the scraper.
    """
    logger = logging.getLogger("goc_scraper")
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers if function is called multiple times
    if logger.handlers:
        return logger
    
    # Compute log file path relative to project root
    project_root = Path(__file__).resolve().parents[2]
    log_dir = project_root / "logs" / "GOC"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "goc_scraper.log"
    
    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Rotating file handler (max 10MB, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


logger = setup_logging()


# ============================================================================
# PATH CONFIGURATION
# ============================================================================

# Compute directories relative to this file
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data" / "GOC"
JOBS_LIST_PATH = PROJECT_ROOT / "list-of-jobs.txt"

# Create necessary directories
(DATA_ROOT / "search_html").mkdir(parents=True, exist_ok=True)
(DATA_ROOT / "job_html").mkdir(parents=True, exist_ok=True)
(DATA_ROOT / "jobs_json").mkdir(parents=True, exist_ok=True)


# ============================================================================
# CONSTANTS
# ============================================================================

BASE_URL = "https://psjobs-emploisfp.psc-cfp.gc.ca/psrs-srfp/applicant/page2440"
BASE_HOST = "https://psjobs-emploisfp.psc-cfp.gc.ca"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

SEARCH_TIMEOUT = 60000  # 60 seconds
JOB_TIMEOUT = 60000


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def slugify_query(query: str) -> str:
    """
    Convert a query string to a filesystem-safe slug.
    
    Args:
        query: Original query string (e.g., "Data Analyst")
    
    Returns:
        Slugified string (e.g., "data_analyst")
    """
    slug = query.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug


def load_queries_from_file(path: Path) -> List[str]:
    """
    Load job title queries from a text file (one per line).
    
    Args:
        path: Path to the file containing queries
    
    Returns:
        List of query strings (stripped, non-empty lines)
    """
    if not path.exists():
        logger.warning(f"Query file not found: {path}")
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Loaded {len(queries)} queries from {path}")
    return queries


def extract_poster_id(url: str) -> Optional[str]:
    """
    Extract the poster ID from a job URL.
    
    Args:
        url: Job URL (e.g., ".../page1800?poster=2373241")
    
    Returns:
        Poster ID string or None if not found
    """
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        poster_id = params.get('poster', [None])[0]
        return poster_id
    except Exception as e:
        logger.error(f"Failed to extract poster_id from {url}: {e}")
        return None


def clean_text(text: str) -> str:
    """
    Clean extracted text by normalizing whitespace and removing extra blank lines.
    
    Args:
        text: Raw text string
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def extract_text_from_section(page: Page, selector: str) -> str:
    """
    Extract inner text from a section identified by CSS selector.
    
    Args:
        page: Playwright page object
        selector: CSS selector for the section
    
    Returns:
        Extracted text or empty string
    """
    try:
        element = page.query_selector(selector)
        if element:
            return clean_text(element.inner_text())
    except Exception as e:
        logger.debug(f"Could not extract text from selector '{selector}': {e}")
    
    return ""


# ============================================================================
# SEARCH FUNCTIONS
# ============================================================================

def build_search_url(query: str, page_number: int = 1) -> str:
    """
    Build a search URL for the GC Jobs portal.
    
    Args:
        query: Job title search query
        page_number: Page number for pagination (1-indexed)
    
    Returns:
        Full search URL with encoded parameters
    """
    params = {
        'tab': '1',
        'title': query,
        'locationsFilter': '',
        'departments': '',
        'officialLanguage': '',
        'referenceNumber': '',
        'selectionProcessNumber': '',
        'search': 'Search jobs',
        'log': 'false'
    }
    
    if page_number > 1:
        params['requestedPage'] = str(page_number)
        params['fromPage'] = str(page_number - 1)
    
    query_string = urlencode(params)
    return f"{BASE_URL}?{query_string}"


def save_search_html(html: str, query_slug: str, page_number: int) -> str:
    """
    Save search results HTML to disk.
    
    Args:
        html: Raw HTML content
        query_slug: Slugified query string
        page_number: Page number
    
    Returns:
        Path to saved file
    """
    filename = f"{query_slug}_page{page_number}.html"
    filepath = DATA_ROOT / "search_html" / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return str(filepath)


def _save_debug_html(page: Page, query_slug: str, page_number: int, suffix: str) -> None:
    """
    Save debug HTML for troubleshooting.
    
    Args:
        page: Playwright page object
        query_slug: Slugified query string
        page_number: Page number
        suffix: Descriptive suffix for the filename
    """
    debug_dir = DATA_ROOT / "debug_html"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{query_slug}_page{page_number}_{suffix}.html"
    filepath = debug_dir / filename
    
    html = page.content()
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"Saved debug HTML to {filepath}")


def fetch_search_page(page: Page, query: str, query_slug: str, page_number: int) -> None:
    """
    Navigate to search page and perform a form-based search.
    
    For the first page, we navigate to the search form and submit it.
    For subsequent pages, we use the pagination links.
    
    Args:
        page: Playwright page object
        query: The actual search query text
        query_slug: Slugified query string for debug output
        page_number: Page number for debug output
    
    Raises:
        PWTimeout: If page load times out or search results container doesn't appear
    """
    if page_number == 1:
        # Navigate to the main search page
        search_form_url = "https://psjobs-emploisfp.psc-cfp.gc.ca/psrs-srfp/applicant/page2440?fromMenu=true"
        logger.debug(f"Navigating to search form: {search_form_url}")
        page.goto(search_form_url, wait_until="domcontentloaded", timeout=SEARCH_TIMEOUT)
        
        # Wait for the title input field to be present
        try:
            page.wait_for_selector("#title", timeout=SEARCH_TIMEOUT)
        except PWTimeout:
            logger.warning(f"Search form not found")
            _save_debug_html(page, query_slug, page_number, "no_form")
            raise
        
        # Clear any existing text and input the search query
        logger.debug(f"Filling search form with query: '{query}'")
        page.fill("#title", query)
        
        # Click the search button
        logger.debug(f"Clicking search button")
        page.click("#search")
        
        # Wait for navigation to complete
        page.wait_for_load_state("domcontentloaded", timeout=SEARCH_TIMEOUT)
    
    # Wait for the search results container to appear
    try:
        page.wait_for_selector("#searchResults", timeout=SEARCH_TIMEOUT)
    except PWTimeout:
        logger.warning(f"Search results container (#searchResults) not found")
        _save_debug_html(page, query_slug, page_number, "no_container")
        raise
    
    # Wait for the results list (ol.posterInfo) to appear - this indicates results are loaded
    try:
        page.wait_for_selector("ol.posterInfo", timeout=15000)
        logger.debug(f"Results list (ol.posterInfo) found, checking for job items")
    except PWTimeout:
        logger.warning(f"No results list (ol.posterInfo) found")
        logger.warning(f"This may indicate 0 results for this query")
        _save_debug_html(page, query_slug, page_number, "no_results")
        # Do NOT raise here - let extract_job_urls_from_search handle empty results
        return
    
    # Give a moment for any dynamic content to fully render
    page.wait_for_timeout(1000)


def extract_job_urls_from_search(page: Page) -> List[str]:
    """
    Extract all job posting URLs from a search results page.
    
    Args:
        page: Playwright page object on a search results page
    
    Returns:
        List of absolute job URLs
    """
    job_urls = []
    
    try:
        # First check if the results list exists
        results_list = page.query_selector("ol.posterInfo")
        if not results_list:
            logger.debug("No ol.posterInfo element found - likely 0 results")
            return job_urls
        
        # Find all job links within search results
        # The HTML shows: <li class="searchResult"> ... <a href="/psrs-srfp/applicant/page1800?poster=2370982">
        job_links = page.query_selector_all("ol.posterInfo li.searchResult a[href*='page1800']")
        
        logger.debug(f"Found {len(job_links)} job link elements")
        
        for link in job_links:
            href = link.get_attribute('href')
            if href and 'poster=' in href:
                # Convert to absolute URL
                absolute_url = urljoin(BASE_HOST, href)
                if absolute_url not in job_urls:
                    job_urls.append(absolute_url)
                    logger.debug(f"Extracted job URL: {absolute_url}")
        
        logger.info(f"Extracted {len(job_urls)} unique job URLs from search page")
    
    except Exception as e:
        logger.error(f"Error extracting job URLs: {e}", exc_info=True)
    
    return job_urls


def has_next_page(page: Page) -> Optional[str]:
    """
    Check if there is a 'Next' page in pagination and return its URL.
    
    Args:
        page: Playwright page object on a search results page
    
    Returns:
        Absolute URL to next page, or None if no next page exists
    """
    try:
        # Look for pagination links
        pagelinks = page.query_selector(".pagelinks")
        if not pagelinks:
            return None
        
        # Find all links within pagination
        links = pagelinks.query_selector_all("a")
        
        for link in links:
            text = link.inner_text().strip().lower()
            if 'next' in text:
                href = link.get_attribute('href')
                if href:
                    return urljoin(BASE_HOST, href)
        
    except Exception as e:
        logger.debug(f"Error checking for next page: {e}")
    
    return None


# ============================================================================
# JOB DETAIL FUNCTIONS
# ============================================================================

def save_job_html(job_html: str, poster_id: str) -> str:
    """
    Save job detail page HTML to disk.
    
    Args:
        job_html: Raw HTML content of job page
        poster_id: Unique poster ID
    
    Returns:
        Path to saved file
    """
    filename = f"{poster_id}.html"
    filepath = DATA_ROOT / "job_html" / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(job_html)
    
    return str(filepath)


def save_job_json(job_data: Dict) -> str:
    """
    Save parsed job data as JSON to disk.
    
    Args:
        job_data: Dictionary containing job details
    
    Returns:
        Path to saved JSON file
    """
    poster_id = job_data.get('poster_id', 'unknown')
    filename = f"{poster_id}.json"
    filepath = DATA_ROOT / "jobs_json" / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, indent=2, ensure_ascii=False)
    
    return str(filepath)


# ============================================================================
# ALTERNATE FORMAT DETECTION AND EXTRACTION
# ============================================================================

def detect_alternate_format(page: Page) -> bool:
    """
    Detect if the job page uses the alternate format.
    
    The alternate format has:
    - A centered fieldset with inline reference number and selection process
    - Department and location in text-center div
    - No labeled fields with <b> or <strong> tags
    
    Args:
        page: Playwright page object
    
    Returns:
        True if alternate format detected, False otherwise
    """
    try:
        # Check for the characteristic "rightRefNumberWithPadding" div
        ref_div = page.query_selector("div.rightRefNumberWithPadding")
        if ref_div:
            return True
        
        # Check for fieldset with text-center class
        fieldset = page.query_selector("fieldset div.text-center")
        if fieldset:
            # Check if it contains inline reference/department info
            text = clean_text(fieldset.inner_text())
            if "reference number" in text.lower() or "selection process" in text.lower():
                return True
    
    except Exception as e:
        logger.debug(f"Error detecting alternate format: {e}")
    
    return False


def extract_alternate_reference_number(page: Page) -> str:
    """Extract reference number from alternate format."""
    try:
        # Look for div.rightRefNumberWithPadding
        ref_div = page.query_selector("div.rightRefNumberWithPadding")
        if ref_div:
            text = ref_div.inner_text()
            # Pattern: "Reference number: XXX"
            match = re.search(r'Reference number:\s*([^\n<]+)', text, re.IGNORECASE)
            if match:
                return clean_text(match.group(1))
    except Exception as e:
        logger.debug(f"Error extracting alternate reference number: {e}")
    return ""


def extract_alternate_selection_process(page: Page) -> str:
    """Extract selection process number from alternate format."""
    try:
        ref_div = page.query_selector("div.rightRefNumberWithPadding")
        if ref_div:
            text = ref_div.inner_text()
            # Pattern: "Selection process number: XXX"
            match = re.search(r'Selection process number:\s*([^\n<]+)', text, re.IGNORECASE)
            if match:
                return clean_text(match.group(1))
    except Exception as e:
        logger.debug(f"Error extracting alternate selection process: {e}")
    return ""


def extract_alternate_department(page: Page) -> str:
    """Extract department from alternate format (text-center fieldset)."""
    try:
        fieldset = page.query_selector("fieldset div.text-center")
        if fieldset:
            # Get all text content and find department lines
            text = fieldset.inner_text()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            dept_parts = []
            for line in lines:
                lower = line.lower()
                # Stop at location info
                if '(' in line and any(prov in lower for prov in ['ontario', 'quebec', 'alberta', 'british columbia', 'manitoba']):
                    break
                # Stop at classification codes
                if re.match(r'^[A-Z]{2}-\d{2}', line):
                    break
                # Stop at salary
                if '$' in line:
                    break
                # Stop at closing date
                if 'closing date' in lower:
                    break
                # Stop at "for further information"
                if 'for further information' in lower or 'please visit' in lower:
                    break
                # Skip reference numbers
                if 'reference number' in lower or 'selection process' in lower:
                    continue
                # Skip apply online
                if 'apply online' in lower or 'who can apply' in lower:
                    continue
                # Skip tenure types
                if any(tenure in lower for tenure in ['acting', 'assignment', 'deployment', 'indeterminate', 'secondment', 'specified period']):
                    continue
                
                # Add valid department lines
                dept_parts.append(line)
            
            if dept_parts:
                # Join with " - " for dept and branch
                return ' - '.join(dept_parts[:2]) if len(dept_parts) >= 2 else dept_parts[0]
    except Exception as e:
        logger.debug(f"Error extracting alternate department: {e}")
    return ""


def extract_alternate_location(page: Page) -> str:
    """Extract location from alternate format."""
    try:
        fieldset = page.query_selector("fieldset div.text-center")
        if fieldset:
            text = fieldset.inner_text()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Look for patterns like "Ottawa (Ontario)" or city names
            for line in lines:
                # Match "City (Province)" pattern
                match = re.search(r'\b([A-Za-z\s]+)\s*\(([A-Za-z\s]+)\)', line)
                if match:
                    city = match.group(1).strip()
                    province = match.group(2).strip()
                    # Verify it's a location (province name appears in list)
                    if any(prov in province.lower() for prov in [
                        'ontario', 'quebec', 'british columbia', 'alberta', 'manitoba', 
                        'saskatchewan', 'nova scotia', 'new brunswick', 'newfoundland',
                        'prince edward island', 'northwest territories', 'yukon', 'nunavut'
                    ]):
                        return f"{city} ({province})"
            
            # Fallback: look for "National Capital Region" or other location keywords
            for line in lines:
                lower = line.lower()
                if 'national capital region' in lower or 'ncr' in lower:
                    return clean_text(line)
    except Exception as e:
        logger.debug(f"Error extracting alternate location: {e}")
    return ""


def extract_alternate_salary(page: Page) -> str:
    """Extract salary from alternate format."""
    try:
        fieldset = page.query_selector("fieldset div.text-center")
        if fieldset:
            text = fieldset.inner_text()
            # Look for salary pattern: $XX,XXX to $XX,XXX
            match = re.search(r'\$[\d,]+\s*to\s*\$[\d,]+', text, re.IGNORECASE)
            if match:
                return clean_text(match.group(0))
    except Exception as e:
        logger.debug(f"Error extracting alternate salary: {e}")
    return ""


def extract_alternate_classification(page: Page) -> str:
    """Extract classification from alternate format."""
    try:
        fieldset = page.query_selector("fieldset div.text-center")
        if fieldset:
            text = fieldset.inner_text()
            # Look for classification pattern: XX-00 (e.g., PM-01, AS-02, IT-03)
            match = re.search(r'\b([A-Z]{2}-\d{2})\b', text)
            if match:
                return clean_text(match.group(1))
    except Exception as e:
        logger.debug(f"Error extracting alternate classification: {e}")
    return ""


def extract_alternate_closing_date(page: Page) -> str:
    """Extract closing date from alternate format."""
    try:
        fieldset = page.query_selector("fieldset div.text-center")
        if fieldset:
            # Look for <p> with <strong> containing "Closing date:"
            strong_elems = fieldset.query_selector_all("strong")
            for elem in strong_elems:
                text = elem.inner_text()
                if "closing date" in text.lower():
                    # Get parent paragraph and extract just the date portion
                    parent_p = page.evaluate("""(elem) => {
                        let p = elem.closest('p');
                        return p ? p.textContent : '';
                    }""", elem)
                    
                    if parent_p:
                        # Remove the "Closing date:" label and clean up
                        date_text = re.sub(r'Closing date:\s*', '', parent_p, flags=re.IGNORECASE).strip()
                        return clean_text(date_text)
    except Exception as e:
        logger.debug(f"Error extracting alternate closing date: {e}")
    return ""


def extract_alternate_who_can_apply(page: Page) -> str:
    """Extract 'who can apply' from alternate format."""
    try:
        fieldset = page.query_selector("fieldset div.text-center")
        if fieldset:
            # Look for <strong> with "Who can apply:"
            strong_elems = fieldset.query_selector_all("strong")
            for elem in strong_elems:
                text = elem.inner_text()
                if "who can apply" in text.lower():
                    # Get the text after the strong element (in the same container)
                    # Look for the next text node or element
                    parent_p = page.evaluate("""(elem) => {
                        // Find the paragraph containing "Who can apply"
                        let container = elem.closest('p, div');
                        if (!container) return '';
                        
                        // Get all text content
                        let fullText = container.textContent;
                        
                        // Find where "Who can apply:" ends
                        let idx = fullText.toLowerCase().indexOf('who can apply:');
                        if (idx === -1) return '';
                        
                        // Get text after the label
                        let afterLabel = fullText.substring(idx + 'who can apply:'.length).trim();
                        
                        // Remove "Apply online" if it appears at the end
                        afterLabel = afterLabel.replace(/Apply online.*$/i, '').trim();
                        
                        return afterLabel;
                    }""", elem)
                    
                    if parent_p:
                        return clean_text(parent_p)
    except Exception as e:
        logger.debug(f"Error extracting alternate who can apply: {e}")
    return ""


def extract_alternate_positions_to_fill(page: Page) -> str:
    """Extract positions to fill from alternate format."""
    try:
        # Look for the specific <strong>Positions to be filled:</strong> pattern
        result = page.evaluate("""() => {
            const strongs = document.querySelectorAll('strong');
            for (let strong of strongs) {
                if (strong.textContent.toLowerCase().includes('positions to be filled')) {
                    // Get the text after the strong tag
                    let parent = strong.parentElement;
                    if (parent) {
                        let fullText = parent.textContent;
                        // Extract text after "Positions to be filled:"
                        let match = fullText.match(/Positions to be filled:\\s*(.+)/i);
                        if (match) {
                            return match[1].trim();
                        }
                    }
                }
            }
            return '';
        }""")
        
        if result:
            return clean_text(result)
        
        # Fallback: check "Intent of the process" section
        intent = extract_section_by_heading_alternate(page, "Intent of the process")
        if intent:
            match = re.search(r'(number to be determined|\d+\s*position)', intent, re.IGNORECASE)
            if match:
                return clean_text(match.group(1))
    except Exception as e:
        logger.debug(f"Error extracting alternate positions to fill: {e}")
    return ""


def extract_alternate_language_requirements(page: Page) -> str:
    """Extract language requirements from alternate format."""
    try:
        # In alternate format, language is often in the essential qualifications
        # Look for paragraphs with IDs that contain "English essential" or "French essential"
        paragraphs = page.query_selector_all("p[id^='somcID']")
        for p in paragraphs:
            text = p.inner_text().strip()
            if re.match(r'^(English|French|Bilingual)\s+(essential|imperative)', text, re.IGNORECASE):
                return clean_text(text)
    except Exception as e:
        logger.debug(f"Error extracting alternate language requirements: {e}")
    return ""


def extract_section_by_heading_alternate(page: Page, heading: str) -> str:
    """
    Extract content from alternate format sections.
    Alternate format uses <h2> for section headers and <p> with IDs for content.
    """
    try:
        h2_elements = page.query_selector_all("h2")
        
        for h2 in h2_elements:
            h2_text = h2.inner_text().strip()
            
            if heading.lower() in h2_text.lower():
                # Collect content until next <h2>
                content_parts = []
                
                # Use JavaScript to get next siblings until we hit another h2
                content = page.evaluate("""(h2) => {
                    let parts = [];
                    let current = h2.nextElementSibling;
                    
                    while (current) {
                        // Stop if we hit another h2
                        if (current.tagName === 'H2') {
                            break;
                        }
                        
                        // Collect text from p, div, ul, ol elements
                        if (['P', 'DIV', 'UL', 'OL'].includes(current.tagName)) {
                            let text = current.textContent.trim();
                            if (text && !text.startsWith('walkme-')) {
                                parts.push(text);
                            }
                        }
                        
                        current = current.nextElementSibling;
                    }
                    
                    return parts.join('\\n');
                }""", h2)
                
                return clean_text(content) if content else ""
    
    except Exception as e:
        logger.debug(f"Error extracting alternate section '{heading}': {e}")
    
    return ""


def extract_requirement_block_alternate(page: Page, block_name: str, req_type: str) -> str:
    """
    Extract requirements from alternate format.
    
    In alternate format, requirements are in <h2> sections like:
    - "In order to be considered..." (essential)
    - "The following will be applied..." (essential - later date)
    - "The following may be applied..." (asset)
    
    Within those sections, there are <p> tags with IDs (somcID...) that contain
    subsections like "EDUCATION:", "EXPERIENCE:", "KNOWLEDGE:", etc.
    
    Multiple labels may appear in the same paragraph!
    
    Args:
        page: Playwright page object
        block_name: Name of the requirement block (e.g., "EDUCATION", "EXPERIENCE")
        req_type: Type of requirement ("essential" or "asset")
    
    Returns:
        Extracted requirements text or empty string
    """
    try:
        # Find the appropriate section based on req_type
        if req_type.lower() == "essential":
            section_headings = [
                "in order to be considered",
                "essential qualifications",
                "the following will be applied"
            ]
        else:  # asset
            section_headings = [
                "the following may be applied",
                "asset qualifications",
                "asset qualification"
            ]
        
        # Use JavaScript to find and extract the content
        result = page.evaluate("""({blockName, reqType, sectionHeadings}) => {
            // Find the h2 matching our section
            let targetH2 = null;
            const h2Elements = document.querySelectorAll('h2');
            
            for (let h2 of h2Elements) {
                const h2Text = h2.textContent.toLowerCase();
                for (let heading of sectionHeadings) {
                    if (h2Text.includes(heading)) {
                        targetH2 = h2;
                        break;
                    }
                }
                if (targetH2) break;
            }
            
            if (!targetH2) return '';
            
            // Collect all <p> elements until the next <h2>
            let paragraphs = [];
            let current = targetH2.nextElementSibling;
            
            while (current) {
                if (current.tagName === 'H2') break;
                if (current.tagName === 'P') {
                    paragraphs.push(current.textContent.trim());
                }
                current = current.nextElementSibling;
            }
            
            // Define all possible block labels
            const blockLabels = [
                'ASSET QUALIFICATION:',
                'EDUCATION:',
                'EXPERIENCE:',
                'KNOWLEDGE:',
                'ABILITY:',
                'ABILITIES:',
                'PERSONAL SUITABILITY',
                'COMPETENCIES:',
                'ORGANIZATIONAL NEEDS:',
                'OPERATIONAL REQUIREMENTS:'
            ];
            
            // Join all paragraphs into one text
            let fullText = paragraphs.join('\\n');
            
            // Find our block by searching for the label
            const searchPattern = new RegExp(blockName + '\\s*:', 'i');
            let startIdx = fullText.search(searchPattern);
            
            if (startIdx === -1) {
                // Try without colon for "PERSONAL SUITABILITY"
                const altPattern = new RegExp(blockName + '(?!\\w)', 'i');
                startIdx = fullText.search(altPattern);
            }
            
            if (startIdx === -1) return '';
            
            // Find where our block's content starts (after the label)
            let contentStart = startIdx;
            // Skip past the label
            let labelMatch = fullText.substring(startIdx).match(/^[A-Z\s]+:?/);
            if (labelMatch) {
                contentStart = startIdx + labelMatch[0].length;
            }
            
            // Find where the next block label starts
            let endIdx = fullText.length;
            for (let label of blockLabels) {
                let labelIdx = fullText.indexOf(label, contentStart);
                if (labelIdx !== -1 && labelIdx < endIdx) {
                    endIdx = labelIdx;
                }
            }
            
            // Extract the content
            let content = fullText.substring(contentStart, endIdx).trim();
            
            // Clean up common non-content patterns
            content = content.replace(/Degree equivalency.*/gi, '');
            content = content.replace(/Information on language requirements.*/gi, '');
            content = content.replace(/http\\S+/g, '');
            
            return content.trim();
        }""", {
            'blockName': block_name,
            'reqType': req_type,
            'sectionHeadings': section_headings
        })
        
        return clean_text(result) if result else ""
    
    except Exception as e:
        logger.debug(f"Error extracting alternate requirement block '{block_name}' ({req_type}): {e}")
    
    return ""


def parse_job_details(page: Page, job_url: str, query: str) -> Dict:
    """
    Parse job details from a job posting page into a structured dictionary.
    
    This function extracts all fields that match the Supabase goc_jobs schema,
    including title, location, requirements, duties, and contact information.
    
    Handles both internal GC Jobs postings and external redirect pages.
    
    Args:
        page: Playwright page object on a job detail page
        job_url: Full URL of the job posting
        query: Original search query used to find this job
    
    Returns:
        Dictionary with job details matching Supabase schema
    """
    poster_id = extract_poster_id(job_url) or ''
    
    job_data = {
        # Core identity
        'url': job_url,
        'poster_id': poster_id,
        'scraped_at': datetime.now(timezone.utc).isoformat(),
        'search_title': query,
        'search_type': 'production',
        
        # External link info (default to False for internal postings)
        'is_external_link': False,
        'external_redirect_url': '',
    }
    
    try:
        # Check if this is an external redirect page
        h1_elem = page.query_selector("main h1, h1")
        if h1_elem:
            h1_text = h1_elem.inner_text().strip()
            
            # Detect external exit pages
            if "you will leave the gc jobs web site" in h1_text.lower():
                logger.info(f"Detected external redirect page for poster {poster_id}")
                
                # Find the external link in main content
                main_elem = page.query_selector("main")
                external_url = ""
                external_text = ""
                
                if main_elem:
                    # Find first <a> tag with http/https href
                    links = main_elem.query_selector_all("a[href^='http']")
                    if links:
                        first_link = links[0]
                        external_url = first_link.get_attribute('href') or ""
                        external_text = clean_text(first_link.inner_text())
                
                logger.info(f"External redirect for poster {poster_id}, redirects to {external_url}")
                
                # Return a clean external posting record
                return {
                    'url': job_url,
                    'poster_id': poster_id,
                    'scraped_at': datetime.now(timezone.utc).isoformat(),
                    'search_title': query,
                    'search_type': 'production',
                    'is_external_link': True,
                    'external_redirect_url': external_url,
                    'title': external_text or "External Posting (Redirect)",
                    'department': '',
                    'location': '',
                    'salary': '',
                    'classification': '',
                    'language_requirements': '',
                    'closing_date': '',
                    'reference_number': '',
                    'selection_process_number': '',
                    'who_can_apply': '',
                    'positions_to_fill': '',
                    'work_environment': '',
                    'duties': '',
                    'essential_education': '',
                    'essential_experience': '',
                    'essential_knowledge': '',
                    'essential_competencies': '',
                    'essential_abilities': '',
                    'asset_education': '',
                    'asset_experience': '',
                    'conditions_of_employment': '',
                    'other_information': (
                        'External posting hosted outside GC Jobs. '
                        'Details not scraped from destination site.'
                    ),
                    'contact_info': '',
                }
        
        # Continue with normal GC Jobs parsing for internal postings
        # Extract title
        title_elem = page.query_selector("h1")
        if title_elem:
            job_data['title'] = clean_text(title_elem.inner_text())
        else:
            job_data['title'] = ''
        
        # Detect alternate format (uses centered fieldset instead of labeled fields)
        is_alternate_format = detect_alternate_format(page)
        
        if is_alternate_format:
            logger.info(f"Detected alternate format for poster {poster_id}, using specialized extraction")
            
            # Extract from the top fieldset (contains ref#, dept, location, salary, etc.)
            job_data['reference_number'] = extract_alternate_reference_number(page)
            job_data['selection_process_number'] = extract_alternate_selection_process(page)
            job_data['department'] = extract_alternate_department(page)
            job_data['location'] = extract_alternate_location(page)
            job_data['salary'] = extract_alternate_salary(page)
            job_data['classification'] = extract_alternate_classification(page)
            job_data['closing_date'] = extract_alternate_closing_date(page)
            job_data['who_can_apply'] = extract_alternate_who_can_apply(page)
            job_data['positions_to_fill'] = extract_alternate_positions_to_fill(page)
            
            # Language requirements may be in the essential section
            job_data['language_requirements'] = extract_alternate_language_requirements(page)
            
        else:
            # Standard format extraction
            # Extract fields from the left information box
            # These are typically in <b>Label</b> followed by text
            
            # Reference number
            job_data['reference_number'] = extract_field_by_label(page, "Reference number")
            
            # Selection process number
            job_data['selection_process_number'] = extract_field_by_label(page, "Selection process number")
            
            # Department/Organization
            job_data['department'] = extract_field_by_label(page, "Organization")
            if not job_data['department']:
                job_data['department'] = extract_field_by_label(page, "Department")
            
            # Location
            job_data['location'] = extract_field_by_label(page, "Location")
            
            # Salary
            job_data['salary'] = extract_field_by_label(page, "Salary")
            
            # Classification/Level
            job_data['classification'] = extract_field_by_label(page, "Level")
            
            # Language requirements
            job_data['language_requirements'] = extract_field_by_label(page, "Language requirements")
            
            # Closing date
            closing_date_raw = extract_field_by_label(page, "Closing date")
            job_data['closing_date'] = parse_closing_date(closing_date_raw)
            
            # Who can apply
            job_data['who_can_apply'] = extract_field_by_label(page, "Who can apply")
            
            # Positions to fill
            job_data['positions_to_fill'] = extract_field_by_label(page, "Positions to be filled")
            if not job_data['positions_to_fill']:
                job_data['positions_to_fill'] = extract_field_by_label(page, "Number of positions")
        
        # Common sections (work for both formats with appropriate extraction)
        # Work environment
        job_data['work_environment'] = (
            extract_section_by_heading_alternate(page, "Work environment") if is_alternate_format 
            else extract_section_by_heading(page, "Work environment")
        )
        
        # Duties
        if is_alternate_format:
            duties = extract_section_by_heading_alternate(page, "Duties")
            if not duties:
                duties = extract_section_by_heading_alternate(page, "Job description")
        else:
            duties = extract_section_by_heading(page, "Duties")
            if not duties:
                duties = extract_section_by_heading(page, "Job description")
        job_data['duties'] = duties
        
        # Essential requirements - Education
        if is_alternate_format:
            job_data['essential_education'] = extract_requirement_block_alternate(page, "EDUCATION", "essential")
        else:
            job_data['essential_education'] = extract_requirement_block(page, "EDUCATION", "essential")
        
        # Essential requirements - Experience
        if is_alternate_format:
            job_data['essential_experience'] = extract_requirement_block_alternate(page, "EXPERIENCE", "essential")
        else:
            job_data['essential_experience'] = extract_requirement_block(page, "EXPERIENCE", "essential")
        
        # Essential requirements - Knowledge
        if is_alternate_format:
            job_data['essential_knowledge'] = extract_requirement_block_alternate(page, "KNOWLEDGE", "essential")
        else:
            job_data['essential_knowledge'] = extract_requirement_block(page, "KNOWLEDGE", "essential")
        
        # Essential competencies
        if is_alternate_format:
            job_data['essential_competencies'] = extract_requirement_block_alternate(page, "PERSONAL SUITABILITY", "essential")
        else:
            job_data['essential_competencies'] = extract_requirement_block(page, "KEY COMPETENCIES", "essential")
            if not job_data['essential_competencies']:
                job_data['essential_competencies'] = extract_requirement_block(page, "COMPETENCIES", "essential")
        
        # Essential abilities
        if is_alternate_format:
            job_data['essential_abilities'] = extract_requirement_block_alternate(page, "ABILITY", "essential")
            if not job_data['essential_abilities']:
                job_data['essential_abilities'] = extract_requirement_block_alternate(page, "ABILITIES", "essential")
        else:
            job_data['essential_abilities'] = extract_requirement_block(page, "ABILITIES", "essential")
            if not job_data['essential_abilities']:
                job_data['essential_abilities'] = extract_requirement_block(page, "ABILITY", "essential")
        
        # Asset requirements - Education
        if is_alternate_format:
            job_data['asset_education'] = extract_requirement_block_alternate(page, "EDUCATION", "asset")
        else:
            job_data['asset_education'] = extract_requirement_block(page, "EDUCATION", "asset")
            if not job_data['asset_education']:
                job_data['asset_education'] = extract_requirement_block(page, "ASSET EDUCATION", "asset")
        
        # Asset requirements - Experience
        if is_alternate_format:
            job_data['asset_experience'] = extract_requirement_block_alternate(page, "EXPERIENCE", "asset")
        else:
            job_data['asset_experience'] = extract_requirement_block(page, "EXPERIENCE", "asset")
            if not job_data['asset_experience']:
                job_data['asset_experience'] = extract_requirement_block(page, "ASSET EXPERIENCE", "asset")
        
        # Conditions of employment
        if is_alternate_format:
            job_data['conditions_of_employment'] = extract_section_by_heading_alternate(page, "Conditions of employment")
        else:
            job_data['conditions_of_employment'] = extract_section_by_heading(page, "Conditions of employment")
            if not job_data['conditions_of_employment']:
                job_data['conditions_of_employment'] = extract_text_from_section(page, "#conditionEmp")
        
        # Other information (catch-all for additional sections)
        other_info_parts = []
        
        # Use appropriate extraction method based on format
        extract_func = extract_section_by_heading_alternate if is_alternate_format else extract_section_by_heading
        
        # Important messages
        important = extract_func(page, "Important messages")
        if important:
            other_info_parts.append(f"Important messages:\n{important}")
        
        # Operational requirements (may also be labeled "OPERATIONAL REQUIREMENTS" in alternate format)
        operational = extract_func(page, "Operational requirements")
        if not operational and is_alternate_format:
            operational = extract_requirement_block_alternate(page, "OPERATIONAL REQUIREMENTS", "asset")
        if operational:
            other_info_parts.append(f"Operational requirements:\n{operational}")
        
        # Organizational needs (alternate format specific)
        if is_alternate_format:
            org_needs = extract_requirement_block_alternate(page, "ORGANIZATIONAL NEEDS", "asset")
            if org_needs:
                other_info_parts.append(f"Organizational needs:\n{org_needs}")
        
        # Our commitment
        commitment = extract_func(page, "Our commitment")
        if commitment:
            other_info_parts.append(f"Our commitment:\n{commitment}")
        
        # Equity, diversity and inclusion
        equity = extract_func(page, "Equity, diversity and inclusion")
        if equity:
            other_info_parts.append(f"Equity, diversity and inclusion:\n{equity}")
        
        # Preference
        preference = extract_func(page, "Preference")
        if preference:
            other_info_parts.append(f"Preference:\n{preference}")
        
        job_data['other_information'] = "\n\n".join(other_info_parts) if other_info_parts else ''
        
        # Contact information
        if is_alternate_format:
            job_data['contact_info'] = extract_section_by_heading_alternate(page, "Contact information")
        else:
            job_data['contact_info'] = extract_text_from_section(page, "#hiringOrgContact")
            if not job_data['contact_info']:
                job_data['contact_info'] = extract_section_by_heading(page, "Hiring organization contact")
        
    except Exception as e:
        logger.error(f"Error parsing job details for {job_url}: {e}")
    
    return job_data


def extract_field_by_label(page: Page, label: str) -> str:
    """
    Extract text following a bold label in the job page.
    
    Args:
        page: Playwright page object
        label: Label text to search for (e.g., "Reference number")
    
    Returns:
        Extracted text or empty string
    """
    try:
        # Try to find <b> tag containing the label
        bold_elements = page.query_selector_all("b")
        
        for elem in bold_elements:
            text = elem.inner_text().strip()
            if label.lower() in text.lower():
                # Get parent element and extract text after the label
                parent = elem.evaluate("el => el.parentElement")
                if parent:
                    full_text = elem.evaluate("el => el.parentElement.innerText")
                    # Remove the label itself from the text
                    result = full_text.replace(text, '', 1).strip()
                    return clean_text(result)
        
        # Alternative: look for dt/dd pairs (definition lists)
        dt_elements = page.query_selector_all("dt")
        for dt in dt_elements:
            dt_text = dt.inner_text().strip()
            if label.lower() in dt_text.lower():
                # Find the corresponding dd
                dd = dt.evaluate("el => el.nextElementSibling")
                if dd:
                    return clean_text(dd.inner_text())
    
    except Exception as e:
        logger.debug(f"Could not extract field '{label}': {e}")
    
    return ""


def extract_section_by_heading(page: Page, heading: str) -> str:
    """
    Extract content from a section identified by a heading.
    
    Args:
        page: Playwright page object
        heading: Heading text to search for (case-insensitive)
    
    Returns:
        Section content or empty string
    """
    try:
        # Look for h2, h3, h4, or b elements containing the heading
        selectors = ["h2", "h3", "h4", "b", "strong"]
        
        for selector in selectors:
            elements = page.query_selector_all(selector)
            
            for elem in elements:
                elem_text = elem.inner_text().strip()
                if heading.lower() in elem_text.lower():
                    # Try to get the next sibling(s) containing content
                    content_parts = []
                    
                    # Get parent section if available
                    parent = elem.evaluate("el => el.closest('div, section, li')")
                    if parent:
                        parent_text = parent.inner_text()
                        # Remove the heading from the content
                        content = parent_text.replace(elem_text, '', 1).strip()
                        if content:
                            return clean_text(content)
                    
                    # If that didn't work, try next siblings
                    next_sibling = elem.evaluate("el => el.nextElementSibling")
                    while next_sibling:
                        sibling_text = next_sibling.inner_text()
                        if sibling_text:
                            content_parts.append(sibling_text)
                        
                        # Stop if we hit another heading
                        tag_name = next_sibling.evaluate("el => el.tagName").lower()
                        if tag_name in ['h1', 'h2', 'h3', 'h4']:
                            break
                        
                        next_sibling = next_sibling.evaluate("el => el.nextElementSibling")
                    
                    if content_parts:
                        return clean_text(" ".join(content_parts))
    
    except Exception as e:
        logger.debug(f"Could not extract section '{heading}': {e}")
    
    return ""


def extract_requirement_block(page: Page, block_label: str, category: str) -> str:
    """
    Extract a specific requirement block (e.g., EDUCATION, EXPERIENCE).
    
    Args:
        page: Playwright page object
        block_label: Label of the requirement block (e.g., "EDUCATION")
        category: "essential" or "asset"
    
    Returns:
        Requirement text or empty string
    """
    try:
        # Look for bold elements with the block label
        bold_elements = page.query_selector_all("b")
        
        for elem in bold_elements:
            text = elem.inner_text().strip().upper()
            if block_label.upper() in text:
                # Check if this is in the right category section
                # by looking at ancestor text
                ancestor = elem.evaluate("el => el.closest('div, section')")
                if ancestor:
                    ancestor_html = ancestor.evaluate("el => el.innerHTML").lower()
                    
                    # Determine if this is essential or asset based on context
                    is_essential = 'essential' in ancestor_html or 'you need' in ancestor_html
                    is_asset = 'asset' in ancestor_html or 'you may need' in ancestor_html
                    
                    if (category == 'essential' and is_essential) or (category == 'asset' and is_asset):
                        # Extract content after this label
                        parent = elem.evaluate("el => el.parentElement")
                        if parent:
                            parent_text = parent.inner_text()
                            # Remove the label
                            content = parent_text.replace(elem.inner_text(), '', 1).strip()
                            if content:
                                return clean_text(content)
        
    except Exception as e:
        logger.debug(f"Could not extract requirement block '{block_label}' ({category}): {e}")
    
    return ""


def parse_closing_date(date_str: str) -> str:
    """
    Parse closing date string into ISO format (YYYY-MM-DD).
    
    Args:
        date_str: Raw date string from the page
    
    Returns:
        ISO formatted date string or empty string if parsing fails
    """
    if not date_str:
        return ""
    
    try:
        # Try common date formats
        # Example: "December 31, 2024" or "2024-12-31"
        
        # Already in ISO format
        if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
            return date_str[:10]
        
        # Try parsing various formats
        from dateutil import parser
        parsed_date = parser.parse(date_str, fuzzy=True)
        return parsed_date.strftime('%Y-%m-%d')
    
    except Exception as e:
        logger.debug(f"Could not parse date '{date_str}': {e}")
        return date_str  # Return original if parsing fails


def fetch_and_parse_job(page: Page, job_url: str, query: str, search_html_path: str) -> Optional[Dict]:
    """
    Navigate to a job detail page, extract all information, and save HTML + JSON.
    
    Args:
        page: Playwright page object
        job_url: URL of the job posting
        query: Original search query
        search_html_path: Path where search HTML was saved (for reference)
    
    Returns:
        Dictionary with job data, or None if scraping failed
    """
    poster_id = extract_poster_id(job_url)
    if not poster_id:
        logger.warning(f"Could not extract poster_id from {job_url}, skipping")
        return None
    
    try:
        # Navigate to job page
        logger.info(f"Scraping job {poster_id} from {job_url}")
        page.goto(job_url, wait_until="domcontentloaded", timeout=JOB_TIMEOUT)
        
        # Optionally wait for network to be idle for more stable parsing
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PWTimeout:
            logger.debug(f"Network not idle after 10s for {job_url}, continuing anyway")
        
        # Save raw HTML
        job_html = page.content()
        html_path = save_job_html(job_html, poster_id)
        logger.debug(f"Saved job HTML to {html_path}")
        
        # Parse job details
        job_data = parse_job_details(page, job_url, query)
        
        # Log the job title
        title = job_data.get('title', 'Unknown Title')
        logger.info(f"Parsed job {poster_id} — '{title}'")
        
        # Save JSON
        json_path = save_job_json(job_data)
        logger.info(f"Saved job JSON to {json_path}")
        
        return job_data
    
    except PWTimeout:
        logger.warning(f"Timeout loading job page: {job_url}")
        return None
    
    except Exception as e:
        logger.error(f"Error scraping job {job_url}: {e}", exc_info=True)
        return None


# ============================================================================
# MAIN SCRAPING WORKFLOW
# ============================================================================

def run_single_query(page: Page, query: str) -> int:
    """
    Run the complete scraping workflow for a single search query.
    
    This includes:
    - Submitting search form
    - Paginating through all search result pages
    - Extracting job URLs from each page
    - Scraping each job's detail page
    
    Args:
        page: Playwright page object
        query: Job title search query
    
    Returns:
        Total number of jobs successfully scraped for this query
    """
    logger.info(f"=" * 80)
    logger.info(f"Starting query: '{query}'")
    logger.info(f"=" * 80)
    
    query_slug = slugify_query(query)
    page_number = 1
    total_jobs_scraped = 0
    all_job_urls = []
    
    # Step 1: Paginate through search results
    while True:
        try:
            logger.info(f"Fetching search page {page_number} for query '{query}'")
            
            # Navigate to search page (first page uses form, subsequent use pagination links)
            fetch_search_page(page, query, query_slug, page_number)
            
            # Save search HTML
            search_html = page.content()
            search_html_path = save_search_html(search_html, query_slug, page_number)
            logger.debug(f"Saved search HTML to {search_html_path}")
            
            # Extract job URLs from this page
            job_urls = extract_job_urls_from_search(page)
            logger.info(f"Page {page_number}: Found {len(job_urls)} job postings")
            
            # Add to our master list (avoid duplicates)
            for url in job_urls:
                if url not in all_job_urls:
                    all_job_urls.append(url)
            
            # Check for next page
            next_page_url = has_next_page(page)
            if next_page_url:
                page_number += 1
                logger.info(f"Next page available, navigating to page {page_number}")
                # Navigate to the next page URL
                page.goto(next_page_url, wait_until="domcontentloaded", timeout=SEARCH_TIMEOUT)
                page.wait_for_timeout(1000)  # Give it a moment to load
            else:
                logger.info(f"No more pages found. Total pages: {page_number}")
                break
        
        except PWTimeout:
            logger.warning(f"Timeout on search page {page_number} for query '{query}', stopping pagination")
            break
        
        except Exception as e:
            logger.error(f"Error on search page {page_number} for query '{query}': {e}")
            break
    
    # Step 2: Scrape each job
    logger.info(f"Total unique job URLs found for query '{query}': {len(all_job_urls)}")
    
    for idx, job_url in enumerate(all_job_urls, 1):
        logger.info(f"Job {idx}/{len(all_job_urls)}")
        
        job_data = fetch_and_parse_job(page, job_url, query, "")
        
        if job_data:
            total_jobs_scraped += 1
            # Placeholder for future Supabase upload
            # upload_to_supabase(job_data)
    
    logger.info(f"Completed query '{query}': {total_jobs_scraped}/{len(all_job_urls)} jobs scraped successfully")
    logger.info(f"=" * 80)
    
    return total_jobs_scraped


def run_batch(page: Page, queries: List[str]) -> None:
    """
    Run the scraping workflow for a batch of queries.
    
    Args:
        page: Playwright page object
        queries: List of job title search queries
    """
    logger.info(f"Starting batch scrape with {len(queries)} queries")
    total_jobs = 0
    
    for idx, query in enumerate(queries, 1):
        logger.info(f"\nQuery {idx}/{len(queries)}: '{query}'")
        jobs_scraped = run_single_query(page, query)
        total_jobs += jobs_scraped
    
    logger.info(f"\n" + "=" * 80)
    logger.info(f"SCRAPING COMPLETED")
    logger.info(f"Total queries: {len(queries)}")
    logger.info(f"Total jobs scraped: {total_jobs}")
    logger.info(f"=" * 80)


# ============================================================================
# SUPABASE PLACEHOLDER
# ============================================================================

def upload_to_supabase(job_data: Dict) -> None:
    """
    Placeholder for future Supabase database upload.
    
    Args:
        job_data: Dictionary containing job details
    """
    # TODO: Implement Supabase integration
    pass


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """
    Main entry point for the GOC job scraper.
    
    Sets up Playwright, loads queries, and runs the scraping workflow.
    """
    logger.info("=" * 80)
    logger.info("GOC Job Scraper Starting")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Data root: {DATA_ROOT}")
    logger.info(f"Jobs list path: {JOBS_LIST_PATH}")
    logger.info("=" * 80)
    
    # Load queries from file
    queries = load_queries_from_file(JOBS_LIST_PATH)
    
    # Fallback to default if no queries loaded
    if not queries:
        logger.warning(f"No queries found in {JOBS_LIST_PATH}, using fallback: ['Data Analyst']")
        queries = ["Data Analyst"]
    
    # Launch Playwright
    logger.info("Launching Playwright browser (Chromium, visible mode)")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        
        try:
            # Run the scraping workflow
            run_batch(page, queries)
        
        finally:
            # Clean up
            logger.info("Closing browser")
            context.close()
            browser.close()
    
    logger.info("GOC Job Scraper finished")


if __name__ == "__main__":
    main()
