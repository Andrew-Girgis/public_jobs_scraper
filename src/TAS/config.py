"""
Configuration for Tasmania Government Job Scraper
"""

# Base URLs
BASE_URL = "https://www.jobs.tas.gov.au"
SEARCH_URL = f"{BASE_URL}/"

# Browser settings
HEADLESS = False  # Set to True to hide browser window

# Fuzzy matching settings
MATCH_THRESHOLD = 80  # Minimum score (0-100) for fuzzy matching
KEYWORDS_FILE = "list-of-jobs-uk.txt"  # Reuse the refined UK keywords list

# Data directories
DATA_DIR = "data/TAS"
JOBS_JSON_DIR = f"{DATA_DIR}/jobs_json"
JOB_HTML_DIR = f"{DATA_DIR}/job_html"
SEARCH_HTML_DIR = f"{DATA_DIR}/search_html"
LOGS_DIR = "logs/TAS"

# Scraper settings
SEARCH_DELAY = 2  # Seconds to wait after search
PAGE_DELAY = 1.5  # Seconds to wait between pages
JOB_DELAY = 1  # Seconds to wait between job scrapes

# Scraper version
SCRAPER_VERSION = "1.0"
