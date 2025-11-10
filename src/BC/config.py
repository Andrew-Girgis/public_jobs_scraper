"""
Configuration for BC Public Service job scraper
"""

from pathlib import Path

# Base URL
BASE_URL = "https://bcpublicservice.hua.hrsmart.com"
SEARCH_URL = f"{BASE_URL}/hr/ats/JobSearch/index/searchType:quick"

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "BC"
HTML_DIR = DATA_DIR / "job_html"
SEARCH_HTML_DIR = DATA_DIR / "search_html"
JSON_DIR = DATA_DIR / "jobs_json"
LOG_DIR = PROJECT_ROOT / "logs" / "BC"

# Ensure directories exist
HTML_DIR.mkdir(parents=True, exist_ok=True)
SEARCH_HTML_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Scraper settings
HEADLESS = False
RESULTS_PER_PAGE = 100  # Max available: 10, 25, 50, 100
REQUEST_TIMEOUT = 30000  # 30 seconds
PAGE_LOAD_WAIT = 2000  # 2 seconds
