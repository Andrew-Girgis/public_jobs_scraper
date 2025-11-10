"""
Configuration settings for the Nova Scotia (NS) job scraper.
"""

from pathlib import Path

# Base URL for Nova Scotia job search
BASE_URL = "https://jobs.novascotia.ca"
SEARCH_URL = f"{BASE_URL}/search/"
HOME_URL = f"{BASE_URL}/home"

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "NS"
JOBS_JSON_DIR = DATA_DIR / "jobs_json"
JOBS_HTML_DIR = DATA_DIR / "job_html"
SEARCH_HTML_DIR = DATA_DIR / "search_html"
LOG_DIR = PROJECT_ROOT / "logs" / "NS"
JOB_LIST_FILE = PROJECT_ROOT / "list-of-jobs.txt"

# Create directories if they don't exist
for directory in [JOBS_JSON_DIR, JOBS_HTML_DIR, SEARCH_HTML_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Scraping settings
HEADLESS = False  # Run browser in headless mode
TIMEOUT = 30000  # Page timeout in milliseconds (30 seconds)
DELAY_BETWEEN_PAGES = 2  # Seconds to wait between page navigations
DELAY_BETWEEN_SEARCHES = 3  # Seconds to wait between keyword searches

# Matching settings (kept for compatibility)
FUZZY_MATCH_THRESHOLD = 60  # Not used - kept for backward compatibility
