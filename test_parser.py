#!/usr/bin/env python
"""Test the ONT parser on a single job"""

from src.ONT import ont_scraper
from src.ONT.models import JobMatch
from playwright.sync_api import sync_playwright

job_match = JobMatch(
    job_id='235898',
    title='Amended - Policy Advisor',
    url='https://www.gojobs.gov.on.ca/Preview.aspx?Language=English&JobID=235898',
    matched_keyword='Policy Advisor',
    match_score=100.0,
    page_number=1
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    page = context.new_page()
    
    job = ont_scraper.parse_job_page(page, job_match)
    
    if job:
        ont_scraper.save_job_json(job)
        print('\n=== ABOUT THE JOB ===')
        print(job.about_the_job if job.about_the_job else 'None')
        print('\n=== WHAT YOU BRING ===')
        print(job.what_you_bring[:400] if job.what_you_bring else 'None')
    
    browser.close()
