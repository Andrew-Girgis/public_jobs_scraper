"""
HTML parsing functions for Tasmania Government Job Scraper
"""

import re
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from .models import TASJob


def parse_job_details(
    html_content: str,
    job_url: str,
    job_id: str,
    job_title: str,
    search_keyword: str,
    matched_keyword: str,
    match_score: int,
    scraper_version: str,
    scraped_at: str
) -> Optional[TASJob]:
    """
    Parse Tasmania job detail page HTML.
    
    Args:
        html_content: Raw HTML content
        job_url: URL of the job posting
        job_id: Job ID extracted from URL
        job_title: Job title (from search results, but we'll get it from page too)
        search_keyword: Keyword used in search
        matched_keyword: Keyword that matched
        match_score: Fuzzy match score
        scraper_version: Version of scraper
        scraped_at: Timestamp when scraped
    
    Returns:
        TASJob object or None if parsing fails
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize all fields
        job_reference = None
        agency = None
        region = None
        location = None
        award = None
        employment_type = None
        closing_date = None
        salary = None
        summary = None
        description_html = ""
        
        # Get job title from h1 (more accurate than search results)
        job_content = soup.find('div', id='job-content')
        if job_content:
            h1 = job_content.find('h1')
            if h1:
                job_title = h1.get_text(strip=True)
        
        # Get agency from orgStrucCrumbs (first line)
        org_crumbs = soup.find('div', class_='orgStrucCrumbs')
        if org_crumbs:
            # Get first line of text (agency name)
            agency_text = org_crumbs.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in agency_text.split('\n') if line.strip()]
            if lines:
                agency = lines[0]
        
        # Find the job details table
        jobs_table = soup.find('div', class_='jobsTableDisplay')
        
        if jobs_table:
            # Parse all rows in the table
            for row in jobs_table.find_all('div', class_='jobsRow'):
                header = row.find('h3', class_='jobsCell')
                value_cell = row.find('div', class_='jobsCell')
                
                if not header or not value_cell:
                    continue
                
                header_text = header.get_text(strip=True).lower()
                value_text = value_cell.get_text(strip=True)
                
                if 'applications close' in header_text:
                    # Extract closing date from time element or text
                    time_elem = value_cell.find('time')
                    if time_elem:
                        closing_date = time_elem.get_text(strip=True)
                    else:
                        closing_date = value_text
                
                elif 'award' in header_text or 'classification' in header_text:
                    award = value_text
                
                elif 'salary' in header_text:
                    salary = value_text
                
                elif 'employment type' in header_text:
                    employment_type = value_text
                
                elif 'region' in header_text:
                    region = value_text
                
                elif 'location' in header_text:
                    location = value_text
                
                elif 'job description' in header_text:
                    summary = value_text
        
        # Get full description HTML from div#job-details
        description_div = soup.find('div', id='job-details')
        
        if description_div:
            description_html = str(description_div)
        else:
            # Fallback: try other selectors
            description_div = soup.find('div', class_='job-description')
            if description_div:
                description_html = str(description_div)
        
        # Create job object
        job = TASJob(
            job_id=job_id,
            job_reference=job_reference,
            job_title=job_title,
            job_url=job_url,
            agency=agency or "",
            region=region,
            location=location,
            award=award,
            employment_type=employment_type,
            closing_date=closing_date or "",
            salary=salary,
            summary=summary,
            description_html=description_html,
            search_keyword=search_keyword,
            matched_keyword=matched_keyword,
            match_score=match_score,
            scraped_at=scraped_at,
            scraper_version=scraper_version
        )
        
        return job
        
    except Exception as e:
        print(f"Error parsing job details: {str(e)}")
        return None


def parse_search_results(html_content: str) -> List[Dict[str, str]]:
    """
    Parse Tasmania job search results HTML.
    
    Args:
        html_content: Raw HTML content
    
    Returns:
        List of job dictionaries with id, title, url
    """
    jobs = []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all job cards
        job_cards = soup.find_all('div', class_='jobCard')
        print(f"      🔍 DEBUG: Found {len(job_cards)} job cards in HTML")
        
        for card in job_cards:
            # Find the job link
            job_link = card.find('a', class_='job-link')
            
            if not job_link:
                continue
            
            # Extract job title
            title_elem = job_link.find('h2', class_='jobTitle')
            if not title_elem:
                continue
            
            job_title = title_elem.get_text(strip=True)
            
            # Extract job URL
            job_url = job_link.get('href', '')
            if job_url.startswith('/'):
                job_url = f"https://careers.pageuppeople.com{job_url}"
            
            # Extract job ID from URL
            # URL pattern: /759/cw/en/job/522719/analyst-various
            job_id_match = re.search(r'/job/(\d+)/', job_url)
            if not job_id_match:
                continue
            
            job_id = job_id_match.group(1)
            
            jobs.append({
                'job_id': job_id,
                'job_title': job_title,
                'job_url': job_url
            })
    
    except Exception as e:
        print(f"Error parsing search results: {str(e)}")
    
    return jobs
