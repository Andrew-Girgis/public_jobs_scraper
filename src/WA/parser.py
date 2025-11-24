"""
HTML Parser for WA Government Jobs
"""

from typing import Optional, List, Dict
from bs4 import BeautifulSoup
import re


def parse_search_results(html: str) -> List[Dict]:
    """
    Parse search results page to extract job listings.
    
    Args:
        html: HTML content of search results page
    
    Returns:
        List of job dictionaries with basic info
    """
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    
    # Find the results table
    table = soup.find('table', class_='Report')
    if not table:
        return jobs
    
    # Find all job rows (skip header row)
    rows = table.find_all('tr')
    for row in rows:
        # Skip header rows
        if row.find('th'):
            continue
        
        cells = row.find_all('td')
        if len(cells) < 8:
            continue
        
        # Extract job title and URL
        job_title_cell = cells[2]
        job_link = job_title_cell.find('a')
        
        if not job_link:
            continue
        
        job_title = job_link.get_text(strip=True)
        job_url = job_link.get('href', '')
        
        # Extract AdvertID from URL (e.g., "page.php?pageID=160&windowUID=0&AdvertID=396139")
        advert_id_match = re.search(r'AdvertID=(\d+)', job_url)
        job_id = advert_id_match.group(1) if advert_id_match else ''
        
        # Extract other fields
        posting_date = cells[0].get_text(strip=True)
        closing_date_cell = cells[1]
        closing_date_div = closing_date_cell.find('div')
        closing_date = closing_date_div.get_text(strip=True) if closing_date_div else cells[1].get_text(strip=True)
        
        branch = cells[3].get_text(strip=True).replace('\xa0', '').strip()
        agency = cells[4].get_text(strip=True)
        classification = cells[5].get_text(strip=True)
        position_number = cells[6].get_text(strip=True)
        location = cells[7].get_text(strip=True)
        
        jobs.append({
            'job_id': job_id,
            'job_title': job_title,
            'job_url': job_url,
            'posting_date': posting_date,
            'closing_date': closing_date,
            'branch': branch if branch else None,
            'agency': agency,
            'classification': classification,
            'position_number': position_number,
            'location': location,
        })
    
    return jobs


def parse_job_details(html: str) -> Dict:
    """
    Parse job details page to extract full job information.
    
    Args:
        html: HTML content of job details page
    
    Returns:
        Dictionary with job details
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    details = {
        'division_name': None,
        'position_number': None,
        'closing_date': None,
        'location': None,
        'job_type': None,
        'salary': None,
        'description_html': '',
        'attachments': []
    }
    
    # Parse job summary section
    summary_content = soup.find('td', class_='aSummaryContent')
    if summary_content:
        # Extract fields from the summary
        sub_headers = summary_content.find_all('div', id='aSubHeaders')
        
        for header_div in sub_headers:
            bold = header_div.find('b')
            if not bold:
                continue
            
            label = bold.get_text(strip=True).rstrip(':').lower()
            
            # Get value - it's after the <br> tag
            # Remove the <b> tag and get remaining text
            value_text = header_div.get_text(separator=' ', strip=True)
            # Remove the label part
            value = value_text.replace(bold.get_text(strip=True), '').strip()
            
            if 'division' in label:
                details['division_name'] = value
            elif 'position no' in label:
                details['position_number'] = value
            elif 'closing date' in label:
                details['closing_date'] = value
            elif 'location' in label:
                details['location'] = value
            elif 'job type' in label:
                details['job_type'] = value
            elif 'salary' in label:
                details['salary'] = value
    
    # Parse job description (About the Job section)
    body_content = soup.find('td', class_='aBodyContent')
    if body_content:
        # Find the "About the Job" section
        # Get all content between "About the Job" header and "Attachments" header
        about_job_header = None
        for header in body_content.find_all('div', id='aSubHeader'):
            if 'About the Job' in header.get_text():
                about_job_header = header
                break
        
        if about_job_header:
            # Collect all content after this header until we hit the next aSubHeader or aAttachments
            description_parts = []
            current = about_job_header.find_next_sibling()
            
            while current:
                # Stop if we hit another subheader (like Attachments)
                if current.name == 'div' and current.get('class') and 'aSubHeaderContainer' in current.get('class', []):
                    break
                if current.name == 'div' and current.get('id') == 'aSubHeader':
                    break
                if current.name == 'div' and current.get('class') and 'aAttachments' in current.get('class', []):
                    break
                
                # Add this element to description
                if current.name in ['p', 'ul', 'ol', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    description_parts.append(str(current))
                
                current = current.find_next_sibling()
            
            details['description_html'] = '\n'.join(description_parts)
    
    # Parse attachments
    attachments_div = soup.find('div', class_='aAttachments')
    if attachments_div:
        links = attachments_div.find_all('a')
        for link in links:
            attachment_url = link.get('href', '')
            attachment_name = link.get_text(strip=True)
            
            if attachment_url and attachment_name:
                # Make URL absolute if needed
                if attachment_url.startswith('/'):
                    attachment_url = f"https://search.jobs.wa.gov.au{attachment_url}"
                
                details['attachments'].append({
                    'name': attachment_name,
                    'url': attachment_url
                })
    
    return details


def has_next_page(html: str) -> bool:
    """
    Check if there is a next page in search results.
    
    Args:
        html: HTML content of search results page
    
    Returns:
        True if next page exists, False otherwise
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for pagination controls - WA uses a different pagination system
    # Check for "Next" button or page numbers
    # This is a simplified check - may need adjustment based on actual pagination
    
    # Look for any link or button with "next" in it
    next_links = soup.find_all('a', string=re.compile(r'next', re.IGNORECASE))
    if next_links:
        return True
    
    # Look for pagination with page numbers
    # If current page is not the last one, there should be higher page numbers
    page_links = soup.find_all('a', href=re.compile(r'page=|offset=', re.IGNORECASE))
    if page_links:
        return True
    
    return False
