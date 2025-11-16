"""
Parser for Queensland Government Job HTML

Handles both search results and job detail pages.
"""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup, Tag


def parse_search_results(html: str) -> List[Dict]:
    """
    Parse Queensland job search results HTML.
    
    Args:
        html: HTML content of search results page
        
    Returns:
        List of job dictionaries with basic information
    """
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    
    # Find all job listings in <ol class="search-results jobs">
    job_list = soup.find('ol', class_='search-results jobs')
    
    if not job_list:
        print("      ⚠️  No job results container found")
        return jobs
    
    job_cards = job_list.find_all('li', recursive=False)
    print(f"      🔍 DEBUG: Found {len(job_cards)} job cards in HTML")
    
    for card in job_cards:
        try:
            # Extract job link and title
            title_link = card.find('h3').find('a') if card.find('h3') else None
            if not title_link:
                continue
            
            job_url = title_link.get('href', '')
            
            # Extract job title and organization from the span
            result_title = title_link.find('span', class_='result-title')
            if not result_title:
                continue
            
            title_text = result_title.get_text(strip=True)
            # Format: "Job Title, Organization"
            if ', ' in title_text:
                job_title, organization = title_text.rsplit(', ', 1)
            else:
                job_title = title_text
                organization = None
            
            # Extract job ID from URL
            job_id = None
            if 'in_jnCounter=' in job_url:
                # Format: in_jnCounter=223096612
                match = re.search(r'in_jnCounter=(\d+)', job_url)
                if match:
                    job_id = match.group(1)
            elif '/jobs/' in job_url:
                # Format: /jobs/QLD-669410-25 or /jobs/QLD-NIISQ668827
                match = re.search(r'/jobs/([^/?]+)', job_url)
                if match:
                    job_id = match.group(1)
            
            if not job_id:
                print(f"      ⚠️  Could not extract job ID from URL: {job_url}")
                continue
            
            # Extract position type (e.g., "Permanent Flexible full-time")
            position_type = None
            type_span = card.find('span', class_='type')
            if type_span:
                position_type = type_span.get_text(strip=True)
            
            # Extract location
            location = None
            location_ul = card.find('ul', class_='location')
            if location_ul:
                location_strong = location_ul.find('strong', class_='locality')
                if location_strong:
                    location = location_strong.get_text(strip=True)
            
            # Extract summary
            summary = None
            summary_div = card.find('div', class_='search-description')
            if summary_div:
                summary = summary_div.get_text(strip=True)
            
            # Extract metadata (classification, closing date)
            meta_div = card.find('div', class_='meta')
            classification = None
            closing_date = None
            
            if meta_div:
                # Classification
                grade_strong = meta_div.find('strong', class_='grade')
                if grade_strong:
                    classification = grade_strong.get_text(strip=True)
                
                # Closing date
                time_tag = meta_div.find('time', class_='date-closes')
                if time_tag:
                    closing_date = time_tag.get_text(strip=True).replace('closes ', '').strip()
            
            # Construct full URL if relative
            if job_url.startswith('/'):
                from . import config
                job_url = f"{config.BASE_URL}{job_url}"
            elif job_url.startswith('jncustomsearch.'):
                from . import config
                job_url = f"{config.BASE_URL}/jobtools/{job_url}"
            
            jobs.append({
                'job_id': job_id,
                'job_title': job_title,
                'organization': organization,
                'job_url': job_url,
                'position_type': position_type,
                'location': location,
                'classification': classification,
                'closing_date': closing_date,
                'summary': summary
            })
            
        except Exception as e:
            print(f"      ⚠️  Error parsing job card: {str(e)}")
            continue
    
    return jobs


def parse_job_details(html: str, job_basic: Dict) -> Optional[Dict]:
    """
    Parse Queensland job detail page HTML.
    
    Args:
        html: HTML content of job detail page
        job_basic: Basic job info from search results
        
    Returns:
        Complete job dictionary or None if parsing fails
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    try:
        # Initialize with basic info
        job = job_basic.copy()
        
        # Extract job title from h1 (more authoritative than search results)
        h1 = soup.find('h1')
        if h1 and 'Job search' not in h1.get_text():
            job['job_title'] = h1.get_text(strip=True)
        
        # Extract organization info (may have organization site link)
        org_div = soup.find('div', string=re.compile(r'Organisation site'))
        if org_div:
            org_text = org_div.get_text(strip=True)
            # Format: "Queensland Health (Organisation site)"
            match = re.search(r'^(.*?)\s*\(', org_text)
            if match:
                job['organization'] = match.group(1).strip()
        
        # Extract details table
        details_table = soup.find('table', class_='striped')
        if details_table:
            rows = details_table.find_all('tr')
            for row in rows:
                th = row.find('th')
                td = row.find('td')
                if not th or not td:
                    continue
                
                header = th.get_text(strip=True).lower()
                value = td.get_text(strip=True)
                
                if 'position status' in header:
                    job['position_status'] = value
                elif 'position type' in header:
                    job['position_type'] = value
                elif 'occupational group' in header:
                    job['occupational_group'] = value
                elif 'classification' in header:
                    job['classification'] = value
                elif 'workplace location' in header:
                    job['location'] = value
                elif 'job ad reference' in header:
                    job['job_reference'] = value
                elif 'closing date' in header:
                    job['closing_date'] = value
                elif 'yearly salary' in header:
                    job['salary_yearly'] = value
                elif 'fortnightly salary' in header:
                    job['salary_fortnightly'] = value
                elif 'total remuneration' in header:
                    job['total_remuneration'] = value
                elif 'job duration' in header:
                    job['job_duration'] = value
                elif 'contact person' in header:
                    job['contact_person'] = value
                elif 'contact details' in header:
                    job['contact_details'] = value
        
        # Extract job overview (full description)
        overview_div = soup.find('div', id='overview')
        if overview_div:
            job['description_html'] = str(overview_div)
        else:
            # Fallback: look for person div
            person_div = soup.find('div', id='person')
            if person_div:
                job['description_html'] = str(person_div)
            else:
                job['description_html'] = ''
        
        return job
        
    except Exception as e:
        print(f"      ❌ Error parsing job details: {str(e)}")
        return None


def has_next_page(html: str) -> bool:
    """
    Check if there is a next page in pagination.
    
    Args:
        html: HTML content of search results page
        
    Returns:
        True if next page exists, False otherwise
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for pagination div
    pagination_div = soup.find('div', id='pagination')
    if not pagination_div:
        return False
    
    # Look for "Next" button
    next_button = pagination_div.find('input', {'name': 'in_storeNextBut', 'value': 'Next'})
    
    return next_button is not None
