"""
Parser for Victoria (Australia) job postings from careers.vic.gov.au
"""

import logging
import re
from typing import Optional
from bs4 import BeautifulSoup
from src.VIC.models import VICJob

logger = logging.getLogger(__name__)


def parse_job_details(html_content: str, job_url: str, job_id: str, search_keyword: str, matched_keyword: Optional[str], match_score: int) -> Optional[VICJob]:
    """
    Parse job details from Victoria job page HTML.
    
    Args:
        html_content: HTML content of the job page
        job_url: URL of the job posting
        job_id: Job ID extracted from URL
        search_keyword: The keyword that led to this job
        matched_keyword: The keyword that matched
        match_score: Fuzzy match score
        
    Returns:
        VICJob object or None if parsing fails
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get job title from h1
        title_elem = soup.find('h1', class_='rpl-header__title')
        job_title = title_elem.get_text(strip=True) if title_elem else "Unknown"
        
        # Get organization
        org_elem = soup.find('div', class_='field--name-field-organisation')
        organization = org_elem.get_text(strip=True) if org_elem else "Unknown"
        
        # Get closing date from the header actions
        closing_elem = soup.find('p', class_='rpl-header-actions__secondary-title')
        closing_date = ""
        if closing_elem:
            closing_text = closing_elem.get_text(strip=True)
            # Extract date from "Applications close Sunday 23 November 2025 at 11.59pm"
            match = re.search(r'Applications close (.+?) at', closing_text)
            if match:
                closing_date = match.group(1).strip()
        
        # Get posted date
        posted_elem = soup.find('time', class_='datetime')
        posted_date = posted_elem.get_text(strip=True) if posted_elem else ""
        
        # Find the overview section with job details
        overview_section = soup.find('div', class_='rpl-content')
        
        # Initialize fields
        work_type = ""
        salary = "Not specified"
        grade = ""
        occupation = ""
        location = ""
        job_reference = ""
        
        if overview_section:
            # Parse the <p> tags with <strong> labels
            for p_tag in overview_section.find_all('p'):
                text = p_tag.get_text(strip=True)
                
                if text.startswith('Work Type:'):
                    work_type = text.replace('Work Type:', '').strip()
                elif text.startswith('Salary:'):
                    salary = text.replace('Salary:', '').strip()
                elif text.startswith('Grade:'):
                    grade = text.replace('Grade:', '').strip()
                elif text.startswith('Occupation:'):
                    occupation = text.replace('Occupation:', '').strip()
                elif text.startswith('Location:'):
                    location = text.replace('Location:', '').strip()
                elif text.startswith('Reference:'):
                    job_reference = text.replace('Reference:', '').strip()
        
        # Get description
        description_div = soup.find('div', class_='field--name-description')
        summary = ""
        description_html = ""
        
        if description_div:
            # Get full HTML for description
            description_html = str(description_div)
            # Get text summary (first 500 chars)
            summary = description_div.get_text(strip=True)[:500]
        
        # Get logo URL
        logo_elem = soup.find('img', class_='rpl-header__logo')
        logo_url = None
        if logo_elem and logo_elem.get('src'):
            logo_url = logo_elem.get('src')
            if logo_url and not logo_url.startswith('http'):
                logo_url = f"https://www.careers.vic.gov.au{logo_url}"
        
        # Create job object
        job = VICJob(
            job_id=job_id,
            job_reference=job_reference,
            job_title=job_title,
            job_url=job_url,
            organization=organization,
            location=location,
            work_type=work_type,
            grade=grade,
            occupation=occupation,
            posted_date=posted_date,
            closing_date=closing_date,
            salary=salary,
            summary=summary,
            description_html=description_html,
            logo_url=logo_url,
            search_keyword=search_keyword,
            matched_keyword=matched_keyword,
            match_score=match_score
        )
        
        return job
        
    except Exception as e:
        logger.error(f"Error parsing job {job_id}: {str(e)}")
        return None


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
        job_divs = soup.find_all('div', class_='job-searchResult')
        
        for job_div in job_divs:
            try:
                # Get job title and URL
                title_link = job_div.find('a', class_='rpl-text-link')
                if not title_link:
                    continue
                
                job_url = title_link.get('href', '')
                if not job_url:
                    continue
                
                # Make absolute URL
                if job_url.startswith('/'):
                    job_url = f"https://www.careers.vic.gov.au{job_url}"
                
                # Extract job ID from URL (e.g., /job/senior-data-analyst-45449)
                job_id_match = re.search(r'/job/.+-(\d+)$', job_url)
                if not job_id_match:
                    continue
                job_id = job_id_match.group(1)
                
                # Get job title from h3
                h3_elem = title_link.find('h3')
                job_title = h3_elem.get_text(strip=True) if h3_elem else "Unknown"
                
                jobs.append({
                    'job_id': job_id,
                    'job_title': job_title,
                    'job_url': job_url
                })
                
            except Exception as e:
                logger.warning(f"Error parsing job result: {e}")
                continue
        
        return jobs
        
    except Exception as e:
        logger.error(f"Error parsing search results: {str(e)}")
        return []
