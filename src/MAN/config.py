"""
Configuration for Manitoba Government Job Scraper
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "MAN"
JOBS_JSON_DIR = DATA_DIR / "jobs_json"
JOBS_HTML_DIR = DATA_DIR / "job_html"
LOG_DIR = PROJECT_ROOT / "logs" / "MAN"
JOB_LIST_FILE = PROJECT_ROOT / "list-of-jobs.txt"

# Create directories if they don't exist
JOBS_JSON_DIR.mkdir(parents=True, exist_ok=True)
JOBS_HTML_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Manitoba job board URL
BASE_URL = "https://jobsearch.gov.mb.ca"
SEARCH_URL = f"{BASE_URL}/search.action"

# Scraper settings
HEADLESS = False  # Set to True to run browser in headless mode
TIMEOUT = 30000  # Page load timeout in milliseconds (30 seconds)
DELAY_BETWEEN_JOBS = (2.0, 4.0)  # Random delay between jobs (min, max) in seconds
