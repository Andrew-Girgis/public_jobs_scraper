"""
Parser for UK job postings from findajob.dwp.gov.uk
"""

import logging
from typing import Optional
from bs4 import BeautifulSoup
from src.UK.models import UKJob

logger = logging.getLogger(__name__)


def parse_job_details(html_content: str, job_url: str, job_id: str, search_keyword: str, matched_keyword: Optional[str], match_score: int) -> Optional[UKJob]:
    """
    Parse job details from UK job page HTML.
    
    Args:
        html_content: HTML content of the job page
        job_url: URL of the job posting
        job_id: Job ID from the URL
        search_keyword: The keyword that led to this job
        matched_keyword: The keyword that matched
        match_score: Fuzzy match score
        
    Returns:
        UKJob object or None if parsing fails
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get job title
        title_elem = soup.find('h1', class_='govuk-heading-l')
        job_title = title_elem.get_text(strip=True) if title_elem else "Unknown"
        
        # Find the details table
        table = soup.find('table', class_='govuk-table')
        if not table:
            logger.warning(f"No details table found for job {job_id}")
            return None
        
        # Extract table data
        details = {}
        rows = table.find_all('tr', class_='govuk-table__row')
        for row in rows:
            header = row.find('th', class_='govuk-table__header')
            cell = row.find('td', class_='govuk-table__cell')
            if header and cell:
                key = header.get_text(strip=True).rstrip(':').lower()
                value = cell.get_text(strip=True)
                details[key] = value
        
        # Get summary/description
        description_div = soup.find('div', class_='govuk-body', itemprop='description')
        summary = ""
        description_html = ""
        
        if description_div:
            # Get full HTML for description
            description_html = str(description_div)
            # Get text summary (first 500 chars)
            summary = description_div.get_text(strip=True)[:500]
        
        # Extract tags (On-site, Hybrid, Permanent, etc.)
        tags = []
        tag_elements = soup.find_all('li', class_='govuk-tag')
        for tag in tag_elements:
            tag_text = tag.get_text(strip=True)
            if tag_text:
                tags.append(tag_text)
        
        # Create job object
        job = UKJob(
            job_id=job_id,
            job_reference=details.get('job reference', ''),
            job_title=job_title,
            job_url=job_url,
            company=details.get('company', ''),
            location=details.get('location', ''),
            remote_working=details.get('remote working'),
            posting_date=details.get('posting date', ''),
            closing_date=details.get('closing date', ''),
            salary=details.get('salary'),
            hours=details.get('hours', ''),
            job_type=details.get('job type', ''),
            summary=summary,
            description_html=description_html,
            tags=tags,
            search_keyword=search_keyword,
            matched_keyword=matched_keyword,
            match_score=match_score
        )
        
        return job
        
    except Exception as e:
        logger.error(f"Error parsing job {job_id}: {str(e)}")
        return None


def extract_job_count(html_content: str) -> int:
    """
    Extract total job count from search results page.
    
    Args:
        html_content: HTML content of search results page
        
    Returns:
        Total number of jobs found
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the legend with results count
        # Format: "Results 1-10 of 115"
        legend = soup.find('legend', class_='search-pos-current')
        if legend:
            text = legend.get_text(strip=True)
            # Extract the total from "Results 1-10 of 115"
            if ' of ' in text:
                total_str = text.split(' of ')[-1].strip()
                return int(total_str)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error extracting job count: {str(e)}")
        return 0


def parse_search_results(html_content: str) -> list:
    """
    Parse job listings from search results page.
    
    Args:
        html_content: HTML content of search results page
        
    Returns:
        List of job dictionaries with basic info
    """
    jobs = []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all job result divs
        job_divs = soup.find_all('div', class_='search-result')
        
        for job_div in job_divs:
            job_id = job_div.get('data-aid')
            if not job_id:
                continue
            
            # Get job title and URL
            title_elem = job_div.find('h3', class_='govuk-heading-s')
            if title_elem:
                link = title_elem.find('a', class_='govuk-link')
                if link:
                    job_title = link.get_text(strip=True)
                    job_url = link.get('href', '')
                    
                    # Make absolute URL
                    if job_url.startswith('/'):
                        job_url = f"https://findajob.dwp.gov.uk{job_url}"
                    
                    jobs.append({
                        'job_id': job_id,
                        'job_title': job_title,
                        'job_url': job_url
                    })
        
        return jobs
        
    except Exception as e:
        logger.error(f"Error parsing search results: {str(e)}")
        return []
