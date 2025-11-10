"""
Test script for Alberta scraper - limited run with visible browser
"""

from playwright.sync_api import sync_playwright
from src.AB.ab_scraper import extract_all_jobs_from_searches, scrape_job_details
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Limited keywords for testing
TEST_KEYWORDS = [
    "data analyst",
    "business analyst", 
    "policy analyst"
]

def main():
    logger.info("=" * 80)
    logger.info("Alberta Scraper - TEST RUN")
    logger.info("=" * 80)
    logger.info(f"Test keywords: {TEST_KEYWORDS}")
    logger.info("Running with VISIBLE browser (headless=False)")
    logger.info("")
    
    with sync_playwright() as p:
        # Launch browser in NON-HEADLESS mode so you can see it
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Search for jobs
            logger.info("Starting job search...")
            all_jobs = extract_all_jobs_from_searches(page, TEST_KEYWORDS)
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("Search Results Summary")
            logger.info("=" * 80)
            logger.info(f"Keywords searched: {len(TEST_KEYWORDS)}")
            logger.info(f"Unique jobs found: {len(all_jobs)}")
            logger.info("")
            
            # Scrape each job
            logger.info("Starting detailed job scraping...")
            logger.info("")
            
            success_count = 0
            error_count = 0
            
            for i, job_info in enumerate(all_jobs, 1):
                job = scrape_job_details(page, job_info, i, len(all_jobs))
                if job:
                    success_count += 1
                else:
                    error_count += 1
                
                # Rate limiting
                time.sleep(1)
            
            # Final summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("TEST RUN COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Successfully scraped: {success_count}")
            logger.info(f"Errors: {error_count}")
            logger.info(f"Total jobs: {len(all_jobs)}")
            logger.info("")
            
            # Wait a bit before closing so you can see the results
            logger.info("Keeping browser open for 5 seconds...")
            time.sleep(5)
            
        finally:
            browser.close()
            logger.info("Browser closed")


if __name__ == "__main__":
    main()
