"""
Configuration for Victoria (Australia) Job Scraper
"""

from pathlib import Path

# Base URL
BASE_URL = "https://www.careers.vic.gov.au"
SEARCH_URL = f"{BASE_URL}/"

# Scraping settings
HEADLESS = False
TIMEOUT = 30000  # 30 seconds

# Delays (in seconds)
DELAY_BETWEEN_SEARCHES = 3  # Between keyword searches
DELAY_BETWEEN_PAGES = 2  # Between pagination
DELAY_BETWEEN_JOBS = 1  # Between job detail scrapes

# Fuzzy matching threshold
MATCH_THRESHOLD = 80

# Data directories
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "VIC"
HTML_DIR = DATA_DIR / "job_html"
JSON_DIR = DATA_DIR / "jobs_json"
SEARCH_HTML_DIR = DATA_DIR / "search_html"
LOGS_DIR = Path(__file__).parent.parent.parent / "logs" / "VIC"

# Scraper version
SCRAPER_VERSION = "1.0.0"

# Keywords file (use same UK list without generic "Manager")
KEYWORDS_FILE = Path(__file__).parent.parent.parent / "list-of-jobs-uk.txt"

# Load keywords from file
with open(KEYWORDS_FILE) as f:
    KEYWORDS = [line.strip() for line in f if line.strip()]
