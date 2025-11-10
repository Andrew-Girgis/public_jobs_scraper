"""
Configuration for Alberta Public Service job scraper
"""

from pathlib import Path

# Base URL for Alberta Public Service job board
BASE_URL = "https://jobpostings.alberta.ca"
SEARCH_URL = f"{BASE_URL}/search/"

# Load search keywords from list-of-jobs.txt
def load_keywords():
    """Load keywords from list-of-jobs.txt file"""
    keywords_file = Path(__file__).parent.parent.parent / "list-of-jobs.txt"
    keywords = []
    
    if keywords_file.exists():
        with open(keywords_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    keywords.append(line)
    
    return keywords

KEYWORDS = load_keywords()

# Selenium settings
WAIT_TIMEOUT = 10  # seconds to wait for elements
PAGE_LOAD_WAIT = 3  # seconds to wait after page loads

# Search settings
RESULTS_PER_PAGE = 25  # Alberta shows 25 results per page
