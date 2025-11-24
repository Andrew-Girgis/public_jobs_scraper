"""
HTML Parser for NSW Job Listings
"""

from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import re


def parse_search_results(html: str) -> List[Dict]:
    """
    Parse search results page to extract job listings.
    
    Args:
        html: HTML content of search results page
    
    Returns:
        List of job dictionaries with basic information
    """
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    
    # Find all job cards
    job_cards = soup.find_all('div', class_='card my-3 job-card col-12')
    
    for card in job_cards:
        try:
            # Extract job title and URL from card header
            header = card.find('div', class_='card-header')
            if not header:
                continue
            
            link = header.find('a')
            if not link:
                continue
            
            job_title = link.get_text(strip=True)
            job_url = link.get('href', '')
            
            # Extract job ID from URL (e.g., /job/lead-data-analyst-553164)
            job_id = job_url.split('/')[-1] if job_url else ""
            
            # Construct full URL
            if job_url and not job_url.startswith('http'):
                from . import config
                job_url = f"{config.BASE_URL}{job_url}"
            
            # Extract additional info from card body
            card_body = card.find('div', class_='card-body')
            
            # Extract summary (first <p> in left column)
            summary = ""
            left_col = card_body.find('div', class_='col col-7') if card_body else None
            if left_col:
                summary_p = left_col.find_all('p')
                if len(summary_p) >= 4:  # The 4th <p> contains the summary
                    summary = summary_p[3].get_text(strip=True)
            
            # Extract organization from right column
            organization = ""
            right_col = card_body.find('div', class_='col col-5') if card_body else None
            if right_col:
                org_h2 = right_col.find('h2')
                if org_h2:
                    organization = org_h2.get_text(strip=True)
            
            # Extract job reference number
            job_reference = ""
            if right_col:
                ref_p = right_col.find('p', class_='job-search-result-ref-no')
                if ref_p:
                    job_reference = ref_p.get_text(strip=True)
            
            # Extract location
            location = ""
            if left_col:
                location_p = left_col.find_all('p')
                if len(location_p) >= 3:  # 3rd <p> contains location
                    location = location_p[2].get_text(strip=True)
            
            # Extract job category
            job_category = ""
            if left_col:
                category_p = left_col.find('p', class_='nsw-tertiary-blue')
                if category_p:
                    job_category = category_p.get_text(strip=True)
            
            # Extract work type
            work_type = ""
            if right_col:
                work_type_p = right_col.find_all('p')
                if len(work_type_p) >= 1:
                    work_type = work_type_p[0].get_text(strip=True)
            
            job = {
                'job_id': job_id,
                'job_reference': job_reference,
                'job_title': job_title,
                'job_url': job_url,
                'organization': organization,
                'location': location,
                'job_category': job_category,
                'work_type': work_type,
                'summary': summary
            }
            
            jobs.append(job)
            
        except Exception as e:
            print(f"Error parsing job card: {str(e)}")
            continue
    
    return jobs


def parse_job_details(html: str, job_basic: Dict) -> Optional[Dict]:
    """
    Parse job detail page to extract full job information.
    
    Args:
        html: HTML content of job detail page
        job_basic: Basic job info from search results
    
    Returns:
        Dictionary with complete job information or None if parsing fails
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    try:
        # Get job title from h1
        title_h1 = soup.find('h1')
        job_title = title_h1.get_text(strip=True) if title_h1 else job_basic.get('job_title', '')
        
        # Extract details from table
        table = soup.find('table', class_='table table-striped job-summary')
        
        organization = job_basic.get('organization', '')
        job_category = job_basic.get('job_category', '')
        location = job_basic.get('location', '')
        job_reference = job_basic.get('job_reference', '')
        work_type = job_basic.get('work_type', '')
        salary_range = ""
        closing_date = ""
        
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    # Get text from cell (handles both direct text and nested <p> tags)
                    value_cell = cells[1]
                    value_p = value_cell.find('p')
                    value = value_p.get_text(strip=True) if value_p else value_cell.get_text(strip=True)
                    
                    if 'organisation' in label or 'entity' in label:
                        organization = value
                    elif 'category' in label:
                        job_category = value
                    elif 'location' in label:
                        location = value
                    elif 'reference' in label:
                        job_reference = value
                    elif 'work type' in label:
                        work_type = value
                    elif 'remuneration' in label or 'package' in label or 'salary' in label:
                        salary_range = value
                    elif 'closing' in label:
                        closing_date = value
        
        # Extract job description - look for the main content div
        description_div = soup.find('div', class_='job-detail-des')
        description_html = ""
        if description_div:
            # The content is inside the div, not in a nested div
            # Remove the outer div attributes and just get the inner HTML
            description_html = ''.join(str(child) for child in description_div.children if str(child).strip())
            # If that's empty, try getting the full div
            if not description_html or description_html == '<!--!-->':
                description_html = str(description_div)
            # Remove Blazor comments like <!--!--> that appear at the start
            # The comment gets parsed as text starting with !
            if description_html.startswith('!'):
                description_html = description_html[1:].lstrip()
        
        job_details = {
            'job_title': job_title,
            'job_reference': job_reference,
            'organization': organization,
            'location': location,
            'job_category': job_category,
            'work_type': work_type,
            'closing_date': closing_date,
            'salary_range': salary_range,
            'summary': job_basic.get('summary', ''),
            'description_html': description_html
        }
        
        return job_details
        
    except Exception as e:
        print(f"Error parsing job details: {str(e)}")
        return None


def has_next_page(html: str) -> bool:
    """
    Check if there is a next page in pagination.
    
    Args:
        html: HTML content of current page
    
    Returns:
        True if next page exists, False otherwise
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find the "Next" button
    next_button = soup.find('button', {
        'aria-label': 'Pagination - Go to Next',
        'title': 'Next'
    })
    
    if not next_button:
        return False
    
    # Check if button is disabled
    classes = next_button.get('class', [])
    return 'disabled' not in classes
