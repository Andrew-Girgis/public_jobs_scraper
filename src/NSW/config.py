"""
Configuration for NSW Job Scraper
"""

from pathlib import Path

# Base URLs
BASE_URL = "https://iworkfor.nsw.gov.au"
JOBS_URL = f"{BASE_URL}/jobs"

# Scraper settings
HEADLESS = False
PAGE_DELAY = 2  # Delay between page loads (seconds)
REQUEST_DELAY = 1  # Delay between requests (seconds)
JOB_DELAY = 2  # Delay when loading job pages

# Keywords
KEYWORDS_FILE = "list-of-jobs-uk.txt"

# Fuzzy matching
MATCH_THRESHOLD = 80

# Data directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "NSW"
JOBS_JSON_DIR = DATA_DIR / "jobs_json"
JOB_HTML_DIR = DATA_DIR / "job_html"
SEARCH_HTML_DIR = DATA_DIR / "search_html"
LOGS_DIR = PROJECT_ROOT / "logs" / "NSW"

# Create directories
for directory in [DATA_DIR, JOBS_JSON_DIR, JOB_HTML_DIR, SEARCH_HTML_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Scraper version
SCRAPER_VERSION = "1.0"
