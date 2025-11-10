"""
Parser module for Nova Scotia job postings.

This module provides detailed parsing functions to extract structured
information from Nova Scotia job pages.
"""

import logging
import re
from typing import List, Optional, Dict
from playwright.sync_api import Page, Locator

logger = logging.getLogger(__name__)


def extract_bullets_from_text(text: str) -> List[str]:
    """
    Extract bullet points from text content.
    
    Args:
        text: Text content that may contain bullet points
    
    Returns:
        List of bullet point strings
    """
    bullets = []
    
    # Split by common bullet markers
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Remove bullet markers (•, -, *, numbers, etc.)
        cleaned = re.sub(r'^[•\-*·○●]\s*', '', line)
        cleaned = re.sub(r'^\d+[\.)]\s*', '', cleaned)
        
        if cleaned:
            bullets.append(cleaned)
    
    return bullets


def parse_salary_range(text: str) -> Dict[str, any]:
    """
    Parse salary range from text.
    
    Args:
        text: Salary range text like "$2,345.67 - $3,456.78 Bi-Weekly"
    
    Returns:
        Dictionary with min_amount, max_amount, frequency, currency
    """
    result = {
        'raw_text': text,
        'min_amount': None,
        'max_amount': None,
        'frequency': 'Bi-Weekly',
        'currency': 'CAD'
    }
    
    if not text:
        return result
    
    # Extract salary amounts
    amounts = re.findall(r'\$[\d,]+\.?\d*', text)
    
    if len(amounts) >= 2:
        try:
            result['min_amount'] = float(amounts[0].replace('$', '').replace(',', ''))
            result['max_amount'] = float(amounts[1].replace('$', '').replace(',', ''))
        except ValueError:
            pass
    elif len(amounts) == 1:
        try:
            result['min_amount'] = float(amounts[0].replace('$', '').replace(',', ''))
        except ValueError:
            pass
    
    # Extract frequency
    if 'annual' in text.lower() or 'yearly' in text.lower():
        result['frequency'] = 'Annual'
    elif 'hourly' in text.lower():
        result['frequency'] = 'Hourly'
    elif 'bi-weekly' in text.lower() or 'biweekly' in text.lower():
        result['frequency'] = 'Bi-Weekly'
    elif 'weekly' in text.lower():
        result['frequency'] = 'Weekly'
    elif 'monthly' in text.lower():
        result['frequency'] = 'Monthly'
    
    return result


def extract_section_content(page: Page, heading_text: str) -> Optional[str]:
    """
    Extract content from a section with a specific heading.
    
    Args:
        page: Playwright page object
        heading_text: The heading text to look for
    
    Returns:
        Section content as string, or None if not found
    """
    try:
        # Find all headings
        headings = page.locator("h2, h3, h4").all()
        
        for heading in headings:
            text = heading.inner_text().strip()
            
            if heading_text.lower() in text.lower():
                # Get parent container
                parent = heading.locator("xpath=ancestor::div[1]")
                
                if parent.count() > 0:
                    content = parent.inner_text().strip()
                    # Remove heading from content
                    content = content.replace(text, '', 1).strip()
                    return content
        
        return None
        
    except Exception as e:
        logger.warning(f"Error extracting section '{heading_text}': {e}")
        return None


def extract_section_bullets(page: Page, heading_text: str) -> List[str]:
    """
    Extract bullet points from a section with a specific heading.
    
    Args:
        page: Playwright page object
        heading_text: The heading text to look for
    
    Returns:
        List of bullet point strings
    """
    content = extract_section_content(page, heading_text)
    
    if content:
        return extract_bullets_from_text(content)
    
    return []


def parse_job_metadata(page: Page) -> Dict[str, any]:
    """
    Parse job metadata from the job page header/table.
    
    Args:
        page: Playwright page object
    
    Returns:
        Dictionary with metadata fields
    """
    metadata = {
        'department': None,
        'location': None,
        'classification': None,
        'competition_number': None,
        'type_of_employment': None,
        'union_status': None,
        'pay_grade': None,
        'salary_range': None
    }
    
    try:
        # Try to find job details table
        detail_rows = page.locator(".job-details-row, .job-field").all()
        
        for row in detail_rows:
            text = row.inner_text().strip()
            
            # Parse different fields
            if 'Department:' in text or 'Department' in text:
                metadata['department'] = text.split(':', 1)[-1].strip()
            elif 'Location:' in text or 'Location' in text:
                metadata['location'] = text.split(':', 1)[-1].strip()
            elif 'Classification:' in text or 'Class:' in text:
                metadata['classification'] = text.split(':', 1)[-1].strip()
            elif 'Competition' in text or 'Competition #' in text:
                metadata['competition_number'] = text.split(':', 1)[-1].strip()
            elif 'Employment Type:' in text or 'Type:' in text:
                metadata['type_of_employment'] = text.split(':', 1)[-1].strip()
            elif 'Union' in text:
                metadata['union_status'] = text.split(':', 1)[-1].strip()
            elif 'Pay Grade:' in text or 'Grade:' in text:
                metadata['pay_grade'] = text.split(':', 1)[-1].strip()
            elif 'Salary' in text or 'Pay Range' in text:
                metadata['salary_range'] = text.split(':', 1)[-1].strip()
        
    except Exception as e:
        logger.warning(f"Error parsing job metadata: {e}")
    
    return metadata


def parse_qualifications_section(page: Page) -> Dict[str, any]:
    """
    Parse the qualifications and experience section with detailed breakdown.
    
    Args:
        page: Playwright page object
    
    Returns:
        Dictionary with qualification fields
    """
    quals = {
        'requirements_intro': None,
        'required_education': None,
        'required_experience': None,
        'required_bullets': [],
        'additional_skills_bullets': [],
        'asset_bullets': [],
        'equivalency_text': None
    }
    
    try:
        # Get the full qualifications section
        content = extract_section_content(page, "Qualifications")
        
        if not content:
            return quals
        
        # Split into subsections
        lines = content.split('\n')
        current_subsection = None
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Identify subsections
            if 'education' in line.lower():
                current_subsection = 'education'
                quals['required_education'] = line
            elif 'experience' in line.lower():
                current_subsection = 'experience'
                quals['required_experience'] = line
            elif 'required' in line.lower() or 'must have' in line.lower():
                current_subsection = 'required'
            elif 'asset' in line.lower() or 'nice to have' in line.lower():
                current_subsection = 'assets'
            elif 'equivalency' in line.lower() or 'equivalent' in line.lower():
                current_subsection = 'equivalency'
                quals['equivalency_text'] = line
            else:
                # Add to current subsection
                if current_subsection == 'required':
                    quals['required_bullets'].append(line)
                elif current_subsection == 'assets':
                    quals['asset_bullets'].append(line)
                elif current_subsection == 'education' and not quals['required_education']:
                    quals['required_education'] = line
                elif current_subsection == 'experience' and not quals['required_experience']:
                    quals['required_experience'] = line
    
    except Exception as e:
        logger.warning(f"Error parsing qualifications section: {e}")
    
    return quals


def extract_links_from_section(page: Page, heading_text: str) -> List[Dict[str, str]]:
    """
    Extract links from a section with a specific heading.
    
    Args:
        page: Playwright page object
        heading_text: The heading text to look for
    
    Returns:
        List of dictionaries with 'text' and 'url' keys
    """
    links = []
    
    try:
        # Find all headings
        headings = page.locator("h2, h3, h4").all()
        
        for heading in headings:
            text = heading.inner_text().strip()
            
            if heading_text.lower() in text.lower():
                # Get parent container
                parent = heading.locator("xpath=ancestor::div[1]")
                
                if parent.count() > 0:
                    # Find all links in this section
                    link_elements = parent.locator("a").all()
                    
                    for link_elem in link_elements:
                        link_text = link_elem.inner_text().strip()
                        link_url = link_elem.get_attribute("href")
                        
                        if link_text and link_url:
                            links.append({
                                'text': link_text,
                                'url': link_url
                            })
        
    except Exception as e:
        logger.warning(f"Error extracting links from section '{heading_text}': {e}")
    
    return links
