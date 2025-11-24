"""
HTML Parser for SA Government Jobs
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
    
    # Find all job rows (skip header row)
    rows = soup.find_all('tr', class_=re.compile(r'(evenrow|oddrow)'))
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
        
        # Extract job title and URL
        job_title_cell = cells[0]
        job_link = job_title_cell.find('a')
        
        if not job_link:
            continue
        
        job_title = job_link.get_text(strip=True)
        job_url = job_link.get('href', '')
        
        # Extract AdvertID from URL (e.g., "page.php?pageID=160&windowUID=0&AdvertID=886090")
        advert_id_match = re.search(r'AdvertID=(\d+)', job_url)
        job_id = advert_id_match.group(1) if advert_id_match else ''
        
        # Extract other fields
        reference_number = cells[1].get_text(strip=True)
        posting_date = cells[2].get_text(strip=True)
        agency = cells[3].get_text(strip=True)
        
        jobs.append({
            'job_id': job_id,
            'job_title': job_title,
            'job_url': job_url,
            'reference_number': reference_number,
            'posting_date': posting_date,
            'agency': agency,
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
        'agency': None,
        'reference_number': None,
        'location': None,
        'job_status': None,
        'eligibility': None,
        'salary': None,
        'closing_date': None,
        'description_html': '',
        'description_text': None,
        'attachments': []
    }
    
    # Find the job details container
    container = soup.find('div', class_='aContainer')
    if not container:
        return details
    
    # Find the aText div which contains all the details
    text_div = container.find('div', class_='aText')
    if not text_div:
        return details
    
    # Get the full HTML content for description
    html_content = str(text_div)
    
    # Extract structured fields using bold tags
    bold_tags = text_div.find_all('b')
    
    for bold in bold_tags:
        label = bold.get_text(strip=True).rstrip(':').lower()
        
        # Get the text after the bold tag (before the next <br> or <b>)
        value = ''
        next_sibling = bold.next_sibling
        
        while next_sibling:
            if next_sibling.name == 'br':
                break
            if next_sibling.name == 'b':
                break
            if isinstance(next_sibling, str):
                value += next_sibling
            else:
                value += next_sibling.get_text()
            next_sibling = next_sibling.next_sibling
        
        value = value.strip()
        
        if not value or value.startswith('<'):
            continue
        
        # Map labels to fields
        if label == 'job reference':
            details['reference_number'] = value
        elif label == 'location':
            details['location'] = value
        elif label == 'job status':
            details['job_status'] = value
        elif label == 'eligibility':
            details['eligibility'] = value
        elif label == 'salary':
            details['salary'] = value
        elif label == 'applications close':
            # Clean up HTML artifacts from closing date
            import re
            value = re.sub(r'</tr>.*$', '', value, flags=re.DOTALL).strip()
            details['closing_date'] = value
        elif not details['agency'] and bold == bold_tags[0]:
            # First bold tag is usually the agency name
            details['agency'] = value
    
    # Extract description HTML - everything between agency and "Applications close"
    # Find the main paragraph content
    paragraphs = text_div.find_all('p')
    if paragraphs:
        description_parts = []
        description_text_parts = []
        for p in paragraphs:
            # Skip the flexibility statement at the end
            if 'Flexibility Statement' in p.get_text():
                break
            description_parts.append(str(p))
            description_text_parts.append(p.get_text(separator=' ', strip=True))
        details['description_html'] = '\n'.join(description_parts)
        details['description_text'] = '\n\n'.join(description_text_parts)
    
    # Extract attachments
    # Find all links to PDF files
    attachment_links = text_div.find_all('a', href=re.compile(r'/files/vacancies/'))
    for link in attachment_links:
        attachment_url = link.get('href', '')
        attachment_name = link.get_text(strip=True)
        
        if attachment_url and attachment_name:
            # Make URL absolute if needed
            if attachment_url.startswith('/'):
                attachment_url = f"https://iworkfor.sa.gov.au{attachment_url}"
            
            details['attachments'].append({
                'name': attachment_name,
                'url': attachment_url
            })
    
    return details
