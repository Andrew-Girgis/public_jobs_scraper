"""
Configuration for Queensland Government Job Scraper
"""

import os
from pathlib import Path

# Base URLs
BASE_URL = "https://smartjobs.qld.gov.au"
SEARCH_URL = f"{BASE_URL}/jobtools/jncustomsearch.jobsearch?in_organid=14904"

# Scraper settings
HEADLESS = False  # Set to True for headless mode
PAGE_DELAY = 2  # Delay between page loads in seconds
REQUEST_DELAY = 1  # Delay between requests in seconds

# Keywords
KEYWORDS_FILE = "list-of-jobs-uk.txt"  # Reuse refined UK keywords list
MATCH_THRESHOLD = 80  # Minimum fuzzy match score (0-100)

# Data directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "QLD"
JOBS_JSON_DIR = DATA_DIR / "jobs_json"
JOB_HTML_DIR = DATA_DIR / "job_html"
SEARCH_HTML_DIR = DATA_DIR / "search_html"
LOGS_DIR = PROJECT_ROOT / "logs" / "QLD"

# Create directories if they don't exist
for directory in [JOBS_JSON_DIR, JOB_HTML_DIR, SEARCH_HTML_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Scraper version
SCRAPER_VERSION = "1.0"
