"""
Parser for Alberta Public Service job postings

Extracts structured data from job posting HTML.
"""

import re
from typing import Optional, List
from bs4 import BeautifulSoup, Tag

from .models import (
    ABJobPosting, ABSource, ABHeader, ABJobInformation, ABSalary,
    ABDiversityInclusion, ABMinistryOverview, ABRoleResponsibilities,
    ABResponsibilityGroup, ABAPSCompetencies, ABQualifications,
    ABRequiredQualifications, ABEquivalency, ABAssets, ABNotes,
    ABResourceLink, ABHowToApply, ABIQASRecommendation, ABClosingStatement,
    ABContactInfo
)


def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean and normalize text."""
    if not text:
        return None
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_salary(salary_text: str) -> ABSalary:
    """
    Parse salary information from text.
    
    Example: "$3,056.50 to $4,006.62 /bi-weekly ($79,774 - $104,572/ year)"
    """
    # Clean the salary text - sometimes it has extra content after
    # Stop at common breaking points
    if 'About Us' in salary_text:
        salary_text = salary_text.split('About Us')[0]
    if 'Role Responsibilities' in salary_text:
        salary_text = salary_text.split('Role Responsibilities')[0]
    
    salary = ABSalary(raw_text=salary_text.strip(), currency="CAD")
    
    # Extract bi-weekly amounts (with or without slash, with or without hyphen)
    biweekly_pattern = r'\$([0-9,]+\.[0-9]{2})\s+to\s+\$([0-9,]+\.[0-9]{2})\s*/?bi-?weekly'
    biweekly_match = re.search(biweekly_pattern, salary_text, re.IGNORECASE)
    if biweekly_match:
        salary.biweekly_min = float(biweekly_match.group(1).replace(',', ''))
        salary.biweekly_max = float(biweekly_match.group(2).replace(',', ''))
        salary.primary_frequency = "bi-weekly"
    
    # Extract annual amounts
    annual_pattern = r'\(\$([0-9,]+)\s*-\s*\$([0-9,]+)/?\s*year\)'
    annual_match = re.search(annual_pattern, salary_text)
    if annual_match:
        salary.annual_min = float(annual_match.group(1).replace(',', ''))
        salary.annual_max = float(annual_match.group(2).replace(',', ''))
    
    return salary


def parse_job_information_section(soup: BeautifulSoup) -> ABJobInformation:
    """Parse the Job Information section."""
    job_info = ABJobInformation()
    
    # The job information is in the first part of the description
    job_desc = soup.find('span', class_='jobdescription')
    if not job_desc:
        return job_info
    
    # Get all the text, looking for the Job Information section
    full_text = job_desc.get_text()
    
    # Find the Job Information section (usually at the beginning)
    # Look for patterns like "Job Title:" through "Salary:"
    
    # Extract each field using regex to handle various spacing
    patterns = {
        'job_title': r'Job Title:\s*(.+?)(?=\n|Job Requisition|$)',
        'job_requisition_id': r'Job Requisition ID:\s*(.+?)(?=\n|Ministry:|$)',
        'ministry': r'Ministry:\s*(.+?)(?=\n|Location:|$)',
        'location': r'Location:\s*(.+?)(?=\n|Full or Part-Time:|$)',
        'full_or_part_time': r'Full or Part-Time:\s*(.+?)(?=\n|Hours of Work:|$)',
        'hours_of_work': r'Hours of Work:\s*(.+?)(?=\n|Permanent/Temporary:|$)',
        'permanent_or_temporary': r'Permanent/Temporary:\s*(.+?)(?=\n|Scope:|$)',
        'scope': r'Scope:\s*(.+?)(?=\n|Closing Date:|$)',
        'closing_date': r'Closing Date:\s*(.+?)(?=\n|Classification:|$)',
        'classification': r'Classification:\s*(.+?)(?=\n|Salary:|$)',
        'salary': r'Salary:\s*(.+?)(?=\n\n|The Government of Alberta|$)',
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
        if match:
            value = clean_text(match.group(1))
            if value:
                if field == 'salary':
                    job_info.salary = parse_salary(value)
                else:
                    setattr(job_info, field, value)
    
    return job_info


def parse_section_with_heading(element: Tag, heading_text: str) -> tuple[Optional[str], List[str]]:
    """
    Parse a section that has a heading (h2) and paragraphs/lists.
    
    Returns:
        Tuple of (heading, body_paragraphs)
    """
    if not element:
        return None, []
    
    heading = None
    body = []
    
    # Find the heading
    h2 = element.find('h2')
    if h2:
        heading = clean_text(h2.get_text())
    
    # Get all paragraphs and list items
    for child in element.find_all(['p', 'ul', 'li'], recursive=False):
        if child.name == 'ul':
            # Process list items
            for li in child.find_all('li'):
                text = clean_text(li.get_text())
                if text:
                    body.append(text)
        elif child.name == 'p':
            text = clean_text(child.get_text())
            if text and text != heading:
                body.append(text)
    
    return heading, body


def parse_ministry_overview(soup: BeautifulSoup, full_text: str) -> ABMinistryOverview:
    """Parse the Ministry Overview section (if present) or About Us section."""
    ministry = ABMinistryOverview()
    
    # First, try to find an "About Us" section (alternative to Ministry Overview)
    about_us_div = None
    for div in soup.find_all('div', style=re.compile(r'padding')):
        h2 = div.find('h2')
        if h2 and 'About Us' in h2.get_text():
            about_us_div = div
            break
    
    if about_us_div:
        # Parse About Us section
        ministry.heading = 'About Us'
        for p in about_us_div.find_all('p'):
            text = clean_text(p.get_text())
            if text and len(text.split()) > 5:
                ministry.body.append(text)
        return ministry
    
    # Otherwise, look for ministry description in the text
    # Usually appears after diversity statement and before Role Responsibilities
    # Pattern: Look for "Alberta [Ministry Name]" or "The Ministry of"
    
    # Find text between diversity policy URL and "Role Responsibilities"
    diversity_idx = full_text.find('diversity-inclusion-policy.aspx')
    role_resp_idx = full_text.find('Role Responsibilities')
    
    if diversity_idx > 0 and role_resp_idx > diversity_idx:
        ministry_section = full_text[diversity_idx:role_resp_idx]
        
        # Split into paragraphs (separated by multiple newlines or periods followed by capital letters)
        paragraphs = []
        current_para = []
        
        for line in ministry_section.split('\n'):
            line = line.strip()
            if not line:
                if current_para:
                    para_text = ' '.join(current_para)
                    if len(para_text) > 30:  # Meaningful paragraph
                        paragraphs.append(clean_text(para_text))
                    current_para = []
            else:
                # Skip URLs
                if not line.startswith('http'):
                    current_para.append(line)
        
        # Add last paragraph
        if current_para:
            para_text = ' '.join(current_para)
            if len(para_text) > 30:
                paragraphs.append(clean_text(para_text))
        
        # Filter out single-word or very short paragraphs
        paragraphs = [p for p in paragraphs if len(p.split()) > 5]
        
        if paragraphs:
            # Look for ministry name in first paragraph
            first_para = paragraphs[0]
            ministry_match = re.search(r'(Alberta [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*|The Ministry of [A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', first_para)
            if ministry_match:
                ministry.heading = ministry_match.group(1)
            
            ministry.body = paragraphs
    
    return ministry


def parse_responsibilities_section(soup: BeautifulSoup) -> ABRoleResponsibilities:
    """Parse the Role Responsibilities section."""
    responsibilities = ABRoleResponsibilities()
    
    # Find the Role Responsibilities div
    role_div = None
    for div in soup.find_all('div', style=re.compile(r'padding')):
        h2 = div.find('h2')
        if h2 and 'Role Responsibilities' in h2.get_text():
            role_div = div
            break
    
    if not role_div:
        return responsibilities
    
    # Get all content
    content = []
    for elem in role_div.find_all(['p', 'ul', 'h2']):
        if elem.name == 'h2':
            continue
        elif elem.name == 'ul':
            for li in elem.find_all('li', recursive=False):
                text = clean_text(li.get_text())
                if text:
                    content.append(('li', text))
        else:
            text = clean_text(elem.get_text())
            if text:
                content.append(('p', text))
    
    # First few paragraphs are intro, then we have responsibility groups
    intro_paragraphs = []
    responsibility_groups = []
    current_group = None
    tagline_set = False
    
    for item_type, text in content:
        if item_type == 'p':
            # Check if this is a tagline (first short enthusiastic paragraph)
            if not tagline_set and len(text) < 300 and ('!' in text or len(text) < 150):
                responsibilities.tagline = text
                tagline_set = True
            # Check if this starts a new responsibility group (underlined text or ends with colon)
            elif text.endswith(':') or (text.count(':') == 1 and len(text) < 150):
                if current_group and current_group.items:
                    responsibility_groups.append(current_group)
                # Extract heading (part before colon if present)
                heading = text.rstrip(':') if text.endswith(':') else text
                current_group = ABResponsibilityGroup(heading=heading, items=[])
            # Check if this looks like "Responsibilities:" or "What You'll Do:"
            elif any(keyword in text.lower() for keyword in ['responsibilities:', 'duties:', "what you'll do:", 'key responsibilities:']):
                if current_group and current_group.items:
                    responsibility_groups.append(current_group)
                current_group = ABResponsibilityGroup(heading=text.rstrip(':'), items=[])
            else:
                if not current_group:
                    # Still in intro section
                    intro_paragraphs.append(text)
                else:
                    # This is a description within a responsibility group
                    current_group.items.append(text)
        elif item_type == 'li':
            if current_group:
                current_group.items.append(text)
            else:
                # Bullet without a group heading - create generic group
                if not responsibility_groups or not current_group:
                    current_group = ABResponsibilityGroup(heading='Responsibilities', items=[])
                current_group.items.append(text)
    
    # Add the last group
    if current_group and current_group.items:
        responsibility_groups.append(current_group)
    
    responsibilities.intro_paragraphs = intro_paragraphs
    responsibilities.responsibility_groups = responsibility_groups
    
    # Look for job description link
    link = role_div.find('a', href=re.compile(r'\.pdf'))
    if link:
        responsibilities.job_description_link_text = clean_text(link.get_text())
        responsibilities.job_description_url = link.get('href')
    
    return responsibilities


def parse_aps_competencies(soup: BeautifulSoup) -> ABAPSCompetencies:
    """Parse the APS Competencies section."""
    competencies = ABAPSCompetencies()
    
    # Find the APS Competencies div
    comp_div = None
    for div in soup.find_all('div', style=re.compile(r'padding')):
        h2 = div.find('h2')
        if h2 and 'APS Competencies' in h2.get_text():
            comp_div = div
            break
    
    if not comp_div:
        return competencies
    
    # Get description paragraphs (before the competency list)
    desc_parts = []
    items = []
    
    # First, collect text from paragraphs
    for elem in comp_div.find_all('p'):
        text = clean_text(elem.get_text())
        if not text:
            continue
        # Skip URL-only paragraphs
        if text.startswith('http'):
            continue
        desc_parts.append(text)
    
    # Then, collect competency items from list items
    for li in comp_div.find_all('li'):
        text = clean_text(li.get_text())
        if text:
            items.append(text)
    
    # If no list items, check if paragraphs contain competencies with bold/strong tags
    if not items:
        for elem in comp_div.find_all(['p', 'li']):
            text = clean_text(elem.get_text())
            if not text:
                continue
            # Check if this is a competency item (contains strong/bold with colon)
            if ':' in text and elem.find(['strong', 'b']):
                items.append(text)
    
    if desc_parts:
        competencies.description = ' '.join(desc_parts[:2])  # First 2 paragraphs as description
    competencies.items = items if items else desc_parts[2:] if len(desc_parts) > 2 else []
    
    return competencies


def parse_qualifications(soup: BeautifulSoup) -> ABQualifications:
    """Parse the Qualifications section."""
    qualifications = ABQualifications()
    
    # Find the Qualifications div
    qual_div = None
    for div in soup.find_all('div', style=re.compile(r'padding')):
        h2 = div.find('h2')
        if h2 and 'Qualifications' in h2.get_text():
            qual_div = div
            break
    
    if not qual_div:
        return qualifications
    
    # Get all text content with structure
    content = qual_div.get_text(separator='\n')
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    current_section = None
    required_items = []
    equivalency_text = []
    equivalency_rules = []
    asset_items = []
    additional_requirements = []
    minimum_standard_items = []
    skills_abilities = []
    willing_able = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for section headers
        if 'Minimum Requirement Standard' in line or 'Minimum Requirements' in line:
            current_section = 'minimum_standard'
            i += 1
            continue
        elif line.startswith('Required:') or 'Education and Work Experience' in line:
            current_section = 'required'
            i += 1
            continue
        elif 'Equivalency:' in line or line.startswith('Equivalency'):
            current_section = 'equivalency'
            # Extract the equivalency text from this line if present
            if ':' in line:
                equiv_text = line.split(':', 1)[1].strip()
                if equiv_text:
                    equivalency_text.append(equiv_text)
            i += 1
            continue
        elif line.startswith('Assets:') or line.startswith('Asset Qualifications:') or line == 'Assets':
            current_section = 'assets'
            i += 1
            continue
        elif 'Additional Requirements' in line:
            current_section = 'additional_requirements'
            i += 1
            continue
        elif 'Skills and Abilities' in line:
            current_section = 'skills_abilities'
            i += 1
            continue
        elif 'Applicants must be willing and able to' in line or 'willing and able' in line.lower():
            current_section = 'willing_able'
            i += 1
            continue
        elif 'Minimum recruitment standards' in line:
            i += 1
            continue
        
        # Add content to current section
        if current_section == 'minimum_standard':
            minimum_standard_items.append(line)
        elif current_section == 'required':
            required_items.append(line)
        elif current_section == 'equivalency':
            equivalency_text.append(line)
            # Look for equivalency rules
            if 'year' in line.lower() and ('=' in line or 'for' in line):
                equivalency_rules.append(line)
        elif current_section == 'assets':
            asset_items.append(line)
        elif current_section == 'additional_requirements':
            additional_requirements.append(line)
        elif current_section == 'skills_abilities':
            skills_abilities.append(line)
        elif current_section == 'willing_able':
            willing_able.append(line)
        
        i += 1
    
    # Now extract from list items with better structure
    for ul in qual_div.find_all('ul'):
        # Find the preceding text to determine which section this belongs to
        prev_text = ''
        prev_elem = ul.find_previous(['p', 'strong', 'b'])
        if prev_elem:
            prev_text = clean_text(prev_elem.get_text()).lower()
        
        for li in ul.find_all('li', recursive=False):
            item_text = clean_text(li.get_text())
            if not item_text:
                continue
                
            if 'asset' in prev_text:
                if item_text not in asset_items:
                    asset_items.append(item_text)
            elif 'skills' in prev_text or 'abilities' in prev_text:
                if item_text not in skills_abilities:
                    skills_abilities.append(item_text)
            elif 'willing' in prev_text or 'able' in prev_text:
                if item_text not in willing_able:
                    willing_able.append(item_text)
            elif 'additional' in prev_text or 'requirement' in prev_text:
                if item_text not in additional_requirements:
                    additional_requirements.append(item_text)
            elif 'required' in prev_text or 'minimum' in prev_text or 'education' in prev_text or 'experience' in prev_text:
                if item_text not in required_items and item_text not in minimum_standard_items:
                    required_items.append(item_text)
    
    # Separate required/minimum standard into education, experience, other
    all_required = minimum_standard_items + required_items
    for item in all_required:
        item_lower = item.lower()
        if 'degree' in item_lower or 'diploma' in item_lower or 'certificate' in item_lower or 'education' in item_lower:
            qualifications.required.education.append(item)
        elif 'experience' in item_lower or 'years' in item_lower or 'year' in item_lower:
            qualifications.required.experience.append(item)
        else:
            qualifications.required.other.append(item)
    
    # Add skills/abilities and additional requirements to "other"
    qualifications.required.other.extend(skills_abilities)
    qualifications.required.other.extend(willing_able)
    qualifications.required.other.extend(additional_requirements)
    
    qualifications.equivalency.text = ' '.join(equivalency_text) if equivalency_text else None
    qualifications.equivalency.rules = equivalency_rules
    qualifications.assets.items = asset_items
    
    return qualifications


def parse_notes(soup: BeautifulSoup) -> ABNotes:
    """Parse the Notes section."""
    notes = ABNotes()
    
    # Find the Notes div
    notes_div = None
    for div in soup.find_all('div', style=re.compile(r'padding')):
        h2 = div.find('h2')
        if h2 and 'Notes' in h2.get_text():
            notes_div = div
            break
    
    if not notes_div:
        return notes
    
    # Also check for "What We Offer" section which may contain benefits info
    offer_div = None
    for div in soup.find_all('div', style=re.compile(r'padding')):
        h2 = div.find('h2')
        if h2 and ('What We Offer' in h2.get_text() or 'What the GoA has to offer' in h2.get_text()):
            offer_div = div
            break
    
    # Get all paragraphs and list items from Notes
    paragraphs = []
    for p in notes_div.find_all('p'):
        text = clean_text(p.get_text())
        if text:
            paragraphs.append(text)
    
    # Get list items (Application Information, What GoA offers, etc.)
    list_items = []
    for ul in notes_div.find_all('ul'):
        for li in ul.find_all('li', recursive=False):
            text = clean_text(li.get_text())
            if text:
                list_items.append(text)
    
    # Parse specific items
    current_list_section = None
    for para in paragraphs:
        # Check for section headers in bold
        if para.startswith('Application Information'):
            current_list_section = 'application_info'
            continue
        elif para.startswith('What the GoA has to offer') or para.startswith('What we offer'):
            current_list_section = 'benefits'
            continue
        
        # Parse actual content
        if 'Term of Employment:' in para or 'permanent' in para.lower() and 'full-time' in para.lower():
            notes.employment_term = para
        elif para.lower().startswith('location:') or 'travel within' in para.lower():
            notes.location_reminder = para
        elif 'written assessment' in para.lower() or 'Police Information Check' in para or 'exempt from' in para:
            notes.assessment_info.append(para)
        elif 'security screening' in para.lower() or 'criminal record check' in para.lower():
            notes.security_screening.append(para)
        elif 'competition may be used' in para.lower():
            notes.reuse_competition_note.append(para)
        elif 'thank all applicants' in para.lower():
            notes.reuse_competition_note.append(para)
        elif 'costs associated' in para.lower() or 'responsibility of the candidate' in para.lower():
            notes.costs_note.append(para)
    
    # Extract resource links from Notes
    for a in notes_div.find_all('a', href=True):
        link_text = clean_text(a.get_text())
        link_url = a.get('href')
        if link_text and link_url:
            # Avoid duplicate text/URL combinations
            if not any(link.url == link_url for link in notes.benefits_and_resources_links):
                notes.benefits_and_resources_links.append(
                    ABResourceLink(label=link_text if link_text != link_url else link_url.split('/')[-1], url=link_url)
                )
    
    # Also extract from "What We Offer" section if present
    if offer_div:
        for ul in offer_div.find_all('ul'):
            for li in ul.find_all('li'):
                text = clean_text(li.get_text())
                if text and 'benefits' in text.lower() or 'pension' in text.lower():
                    # This is benefits info - could be added to a benefits field if needed
                    pass
        
        # Extract links from What We Offer
        for a in offer_div.find_all('a', href=True):
            link_text = clean_text(a.get_text())
            link_url = a.get('href')
            if link_text and link_url:
                if not any(link.url == link_url for link in notes.benefits_and_resources_links):
                    notes.benefits_and_resources_links.append(
                        ABResourceLink(label=link_text if link_text != link_url else link_url.split('/')[-1], url=link_url)
                    )
    
    return notes


def parse_how_to_apply(soup: BeautifulSoup) -> ABHowToApply:
    """Parse the How To Apply section."""
    how_to_apply = ABHowToApply()
    
    # Find "How To Apply" heading
    content = soup.get_text(separator='\n')
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    in_how_to_apply = False
    in_closing_statement = False
    instructions = []
    
    for line in lines:
        if 'How To Apply' in line:
            in_how_to_apply = True
            continue
        elif 'Closing Statement' in line:
            in_how_to_apply = False
            in_closing_statement = True
            continue
        
        if in_how_to_apply and not in_closing_statement:
            if line and not line.startswith('http'):
                instructions.append(line)
    
    how_to_apply.instructions = instructions
    
    return how_to_apply


def parse_closing_statement(soup: BeautifulSoup) -> ABClosingStatement:
    """Parse the Closing Statement section."""
    closing = ABClosingStatement()
    
    # Get closing statement text
    content = soup.get_text(separator='\n')
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    in_closing = False
    closing_lines = []
    
    for line in lines:
        if 'Closing Statement' in line:
            in_closing = True
            continue
        
        if in_closing:
            closing_lines.append(line)
    
    # Parse closing lines
    for line in closing_lines:
        if 'competition may be used' in line.lower():
            closing.reuse_competition_note = line
        elif 'thank all applicants' in line.lower() or 'only individuals selected' in line.lower():
            closing.thanks_and_screening_note = line
        elif 'accommodation' in line.lower():
            closing.accommodation_note = line
        elif '@' in line:
            # Extract contact info
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
            if email_match:
                closing.contact.email = email_match.group(1)
                # Try to extract name before email
                name_match = re.search(r'contact\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s+[A-Z][a-z]+)?)', line, re.IGNORECASE)
                if name_match:
                    closing.contact.name = name_match.group(1)
    
    return closing


def parse_job_details(soup: BeautifulSoup, url: str, keyword: Optional[str] = None) -> ABJobPosting:
    """
    Parse complete job details from HTML.
    
    Args:
        soup: BeautifulSoup object of job page
        url: Job posting URL
        keyword: Search keyword that found this job
    
    Returns:
        ABJobPosting object with all parsed data
    """
    job_posting = ABJobPosting(search_keyword=keyword)
    
    # Source
    job_posting.source = ABSource(url=url)
    
    # Header information
    header = ABHeader()
    job_title_elem = soup.find('h1', id='job-title')
    if job_title_elem:
        header.job_title = clean_text(job_title_elem.get_text())
    
    posting_date_elem = soup.find('p', id='job-date')
    if posting_date_elem:
        date_text = posting_date_elem.get_text()
        match = re.search(r'Posting Date:\s*(.+)', date_text)
        if match:
            header.posting_date = clean_text(match.group(1))
    
    location_elem = soup.find('p', id='job-location')
    if location_elem:
        location_span = location_elem.find('span', class_='jobGeoLocation')
        if location_span:
            header.location_line = clean_text(location_span.get_text())
    
    job_posting.header = header
    
    # Job Information section
    job_posting.job_information = parse_job_information_section(soup)
    
    # Get full text for ministry overview parsing
    job_desc = soup.find('span', class_='jobdescription')
    full_text = job_desc.get_text() if job_desc else ""
    
    # Diversity and Inclusion
    diversity_link = soup.find('a', href=re.compile(r'diversity-inclusion-policy'))
    if diversity_link:
        # Get the paragraph containing this link
        para = diversity_link.find_parent('p')
        if para:
            job_posting.diversity_and_inclusion.statement = clean_text(para.get_text())
    
    # Ministry Overview (if present)
    job_posting.ministry_overview = parse_ministry_overview(soup, full_text)
    
    # Role Responsibilities
    job_posting.role_responsibilities = parse_responsibilities_section(soup)
    
    # APS Competencies
    job_posting.aps_competencies = parse_aps_competencies(soup)
    
    # Qualifications
    job_posting.qualifications = parse_qualifications(soup)
    
    # Notes
    job_posting.notes = parse_notes(soup)
    
    # How To Apply
    job_posting.how_to_apply = parse_how_to_apply(soup)
    
    # Closing Statement
    job_posting.closing_statement = parse_closing_statement(soup)
    
    return job_posting
