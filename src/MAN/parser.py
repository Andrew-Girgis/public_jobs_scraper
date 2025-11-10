"""
Parser for Manitoba Government Job Postings

Parses the job bulletin HTML to extract structured data.
"""

import re
from typing import Optional, List
from bs4 import BeautifulSoup

from .models import (
    MANJob, MANJobPosting, MANSource, MANMetadata, MANSalary,
    MANEmploymentEquity, MANCompetitionNotes, MANPositionOverview,
    MANBenefits, MANConditionsOfEmployment, MANQualifications,
    MANDuties, MANApplicationInstructions, MANApplyToBlock,
    MANScrapingMetadata
)


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_salary(salary_text: str) -> MANSalary:
    """
    Parse salary text like "PM2 $68,106.00 - $87,851.00 per year"
    
    Returns:
        MANSalary object with extracted data
    """
    salary = MANSalary(raw_text=salary_text)
    
    if not salary_text:
        return salary
    
    # Extract classification code (e.g., "PM2", "CL3")
    code_match = re.search(r'\b([A-Z]{2,3}\d+)\b', salary_text)
    if code_match:
        salary.classification_code = code_match.group(1)
    
    # Extract salary range
    amount_pattern = r'\$\s*([\d,]+(?:\.\d{2})?)'
    amounts = re.findall(amount_pattern, salary_text)
    
    if len(amounts) >= 2:
        try:
            salary.min_amount = float(amounts[0].replace(',', ''))
            salary.max_amount = float(amounts[1].replace(',', ''))
        except:
            pass
    elif len(amounts) == 1:
        try:
            salary.min_amount = float(amounts[0].replace(',', ''))
            salary.max_amount = salary.min_amount
        except:
            pass
    
    # Extract frequency
    if 'per hour' in salary_text.lower() or 'hourly' in salary_text.lower():
        salary.frequency = 'per hour'
    elif 'per month' in salary_text.lower() or 'monthly' in salary_text.lower():
        salary.frequency = 'per month'
    else:
        salary.frequency = 'per year'
    
    return salary


def parse_job_details(html_content: str, job_id: str, matched_keyword: str, 
                     match_score: int) -> Optional[MANJob]:
    """
    Parse job details from the bulletin HTML.
    
    Args:
        html_content: HTML content of the bulletin div
        job_id: Job ID
        matched_keyword: Keyword that matched this job
        match_score: Match score
    
    Returns:
        MANJob object if successful, None otherwise
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize job object
        job = MANJob()
        job.scraping_metadata.job_id = job_id
        job.scraping_metadata.matched_keyword = matched_keyword
        job.scraping_metadata.match_score = match_score
        
        # Find the bulletinTextArea div
        text_area = soup.find('div', id='bulletinTextArea')
        if not text_area:
            return None
        
        # Extract job title from h2
        h2 = text_area.find('h2')
        if h2:
            job.job_posting.metadata.job_title = clean_text(h2.get_text())
        
        # Get the main content div (the last div child without id/class that contains all paragraphs)
        main_div = None
        for div in text_area.find_all('div', recursive=False):
            if not div.get('id') and not div.get('class'):
                # Check if this div has h2 (job title)
                if div.find('h2'):
                    main_div = div
                    break
        
        if not main_div:
            return None
        
        all_p = main_div.find_all('p')
        
        # Track what we've seen to extract in order
        seen_conditions = False
        seen_qualifications = False
        seen_duties = False
        seen_apply_to = False
        
        current_section = None
        overview_paragraphs = []
        
        for p in all_p:
            text = clean_text(p.get_text())
            if not text:
                continue
            
            # Check for section headers
            if text == "Conditions of Employment:":
                seen_conditions = True
                current_section = "conditions"
                job.job_posting.conditions_of_employment.heading = text
                continue
            elif text.startswith("Qualifications:"):
                seen_qualifications = True
                current_section = "qualifications"
                job.job_posting.qualifications.heading = "Qualifications"
                continue
            elif text.startswith("Duties:"):
                seen_duties = True
                current_section = "duties"
                job.job_posting.duties.heading = "Duties"
                continue
            
            # Handle metadata extraction from early paragraphs
            if not seen_conditions:
                # Classification title (first emphasis paragraph after h2)
                if p.get('class') and 'emphasis' in p.get('class') and not job.job_posting.metadata.classification_title:
                    job.job_posting.metadata.classification_title = text
                    # Extract classification code
                    code_match = re.search(r'\b([A-Z]{2,3}\d+)\b', text)
                    if code_match:
                        job.job_posting.metadata.classification_code = code_match.group(1)
                
                # Employment types (short paragraphs early in the document)
                elif any(term in text.lower() for term in ['full-time', 'part-time', 'term', 'casual', 'regular']) and len(text) < 100:
                    if not job.job_posting.metadata.employment_types:
                        # Clean up the text
                        types = [t.strip() for t in text.split(';') if t.strip()]
                        job.job_posting.metadata.employment_types = types
                
                # Department (after employment type, before division)
                elif not job.job_posting.metadata.departments and not p.get('class') and \
                     len(text) > 5 and not text.startswith('Advertisement') and \
                     not text.startswith('Salary') and not text.startswith('Closing') and \
                     ' MB' not in text and not any(term in text.lower() for term in ['full-time', 'part-time', 'term']):
                    job.job_posting.metadata.departments = [text]
                
                # Division (comes after department, before location)
                elif job.job_posting.metadata.departments and not job.job_posting.metadata.divisions and \
                     not p.get('class') and not text.startswith('Advertisement') and \
                     not text.startswith('Salary') and not text.startswith('Closing') and \
                     ' MB' not in text and len(text) > 5:
                    job.job_posting.metadata.divisions = [text]
                
                # Location (contains "MB")
                elif ' MB' in text and not job.job_posting.metadata.locations:
                    job.job_posting.metadata.locations = [text]
                
                # Advertisement number
                elif text.startswith('Advertisement Number:'):
                    adv_num = text.replace('Advertisement Number:', '').strip()
                    job.job_posting.metadata.advertisement_number = adv_num
                
                # Salary
                elif text.startswith('Salary'):
                    salary_text = text.replace('Salary(s):', '').replace('Salary:', '').strip()
                    job.job_posting.metadata.salary = parse_salary(salary_text)
                
                # Closing date
                elif text.startswith('Closing Date:'):
                    date_text = text.replace('Closing Date:', '').strip()
                    job.job_posting.metadata.closing_date = date_text
                
                # Employment equity (handled by ID selectors below)
                elif p.get('id') in ['mandatoryEmploymentEquityStatement', 'selectedEmploymentEquityStatement']:
                    pass  # Handled separately below
                
                # Competition notes (emphasis paragraphs OR paragraphs with emphasis spans)
                elif (p.get('class') and 'emphasis' in p.get('class')) or p.find('span', class_='emphasis'):
                    # Get the full text including from emphasis spans
                    emphasis_span = p.find('span', class_='emphasis')
                    check_text = emphasis_span.get_text() if emphasis_span else text
                    
                    if 'eligibility list' in check_text.lower():
                        # Store the full text - might include both eligibility and classification flex
                        full_text = clean_text(p.get_text())
                        if 'competition may also' in full_text.lower() or 'used to source' in full_text.lower():
                            # Split into two parts if both are present
                            parts = full_text.split('. This competition')
                            if len(parts) == 2:
                                job.job_posting.competition_notes.eligibility_list_text = parts[0] + '.'
                                job.job_posting.competition_notes.classification_flex_text = 'This competition' + parts[1]
                            else:
                                job.job_posting.competition_notes.eligibility_list_text = full_text
                        else:
                            job.job_posting.competition_notes.eligibility_list_text = full_text
                    elif 'competition may also' in check_text.lower() or 'used to source' in check_text.lower():
                        job.job_posting.competition_notes.classification_flex_text = clean_text(p.get_text())
                    elif 'competition will be used' in check_text.lower():
                        job.job_posting.competition_notes.usage_text = clean_text(p.get_text())
                
                # Position overview (substantial paragraphs before conditions section)
                elif len(text) > 80 and not p.get('id') and \
                     not (p.get('class') and 'emphasis' in p.get('class')) and \
                     not p.find('span', class_='emphasis'):
                    # Check if this looks like a description paragraph
                    if not text.startswith('Advertisement') and not text.startswith('Salary') and \
                       not text.startswith('Closing') and not text.startswith('Apply') and \
                       not text.startswith('Conditions'):
                        # Check if paragraph contains <br> tags (multi-part content)
                        if p.find('br'):
                            # Split by <br> and extract meaningful parts
                            html_str = str(p)
                            parts = re.split(r'<br\s*/?>', html_str)
                            for part in parts:
                                part_soup = BeautifulSoup(part, 'html.parser')
                                part_text = clean_text(part_soup.get_text())
                                if part_text and len(part_text) > 80:
                                    overview_paragraphs.append(part_text)
                        else:
                            overview_paragraphs.append(text)
        
        # Store overview paragraphs
        if overview_paragraphs:
            job.job_posting.position_overview.summary_paragraphs = overview_paragraphs
        
        # Extract employment equity statements (by ID)
        equity_intro = text_area.find('p', id='mandatoryEmploymentEquityStatement')
        if equity_intro:
            job.job_posting.employment_equity.intro_paragraph = clean_text(equity_intro.get_text())
            # Extract designated groups
            text_lower = equity_intro.get_text().lower()
            groups = []
            if 'women' in text_lower:
                groups.append('women')
            if 'indigenous' in text_lower:
                groups.append('Indigenous people')
            if 'disabilities' in text_lower:
                groups.append('persons with disabilities')
            if 'visible minorities' in text_lower:
                groups.append('visible minorities')
            job.job_posting.employment_equity.designated_groups = groups
        
        equity_factor = text_area.find('p', id='selectedEmploymentEquityStatement')
        if equity_factor:
            job.job_posting.employment_equity.equity_factor_statement = clean_text(equity_factor.get_text())
        
        # Extract Conditions of Employment (ul after "Conditions of Employment:" paragraph)
        conditions_p = main_div.find('span', class_='emphasis', string=re.compile(r'Conditions of Employment:', re.IGNORECASE))
        if conditions_p:
            # Get the parent paragraph
            conditions_p = conditions_p.find_parent('p')
            # Find all ul elements after this paragraph (there may be multiple)
            conditions_items = []
            for sibling in conditions_p.find_next_siblings():
                if sibling.name == 'ul':
                    items = sibling.find_all('li')
                    conditions_items.extend([clean_text(li.get_text()) for li in items])
                elif sibling.name == 'p' and sibling.find('span', class_='emphasis'):
                    # Stop at next section
                    break
            job.job_posting.conditions_of_employment.items = conditions_items
        
        # Extract Qualifications (Essential and Desired)
        qual_p = main_div.find('span', class_='emphasis', string=re.compile(r'Qualifications:', re.IGNORECASE))
        if qual_p:
            # Get the parent paragraph
            qual_p = qual_p.find_parent('p')
            # Get the content after "Qualifications:"
            essential_items = []
            desired_items = []
            current_qual_section = None
            
            # Check the qualifications paragraph itself first for Essential/Desired markers
            html_content_p = str(qual_p)
            text_content_p = qual_p.get_text()
            
            # Check for various Essential/Desired marker formats (flexible to handle typos like "Esssential")
            if re.search(r'<strong>Es+ential:</strong>', html_content_p, re.IGNORECASE) or \
               re.search(r'<u>Es+ential:</u>', html_content_p, re.IGNORECASE) or \
               re.search(r'Es+ential:', text_content_p, re.IGNORECASE):
                current_qual_section = 'essential'
            
            # Track if we've seen first ul (essential) to know second ul is desired
            seen_first_ul = False
            
            # Now iterate through siblings
            for sibling in qual_p.find_next_siblings():
                if sibling.name == 'p':
                    # Check for Essential/Desired markers (flexible with typos)
                    html_content_sibling = str(sibling)
                    if re.search(r'<strong>Es+ential:</strong>', html_content_sibling, re.IGNORECASE) or \
                       re.search(r'<u>Es+ential:</u>', html_content_sibling, re.IGNORECASE):
                        current_qual_section = 'essential'
                        # Check if there are items in this same paragraph
                        ul_in_p = sibling.find('ul')
                        if ul_in_p:
                            items = ul_in_p.find_all('li')
                            essential_items.extend([clean_text(li.get_text()) for li in items])
                    elif re.search(r'<strong>Desired:</strong>', html_content_sibling, re.IGNORECASE) or \
                         re.search(r'<u>Desired:</u>', html_content_sibling, re.IGNORECASE):
                        current_qual_section = 'desired'
                        ul_in_p = sibling.find('ul')
                        if ul_in_p:
                            items = ul_in_p.find_all('li')
                            desired_items.extend([clean_text(li.get_text()) for li in items])
                    elif sibling.find('span', class_='emphasis') and 'Duties:' in sibling.get_text():
                        # Stop at Duties section
                        break
                elif sibling.name == 'strong':
                    # Check for Essential/Desired in <strong> tag (flexible with typos)
                    strong_text = sibling.get_text()
                    if re.search(r'Es+ential:', strong_text, re.IGNORECASE):
                        current_qual_section = 'essential'
                    elif re.search(r'Desired:', strong_text, re.IGNORECASE):
                        current_qual_section = 'desired'
                elif sibling.name == 'u':
                    # Check for Essential/Desired in <u> (underline) tag (flexible with typos)
                    u_text = sibling.get_text()
                    if re.search(r'Es+ential:', u_text, re.IGNORECASE):
                        current_qual_section = 'essential'
                    elif re.search(r'Desired:', u_text, re.IGNORECASE):
                        current_qual_section = 'desired'
                elif sibling.name == 'ul':
                    items = sibling.find_all('li')
                    # Check if this is the second <ul> (Desired) with no explicit marker
                    if seen_first_ul and not desired_items and current_qual_section == 'essential':
                        # Second <ul> after <br> with no "Desired:" marker - assume it's desired
                        desired_items.extend([clean_text(li.get_text()) for li in items])
                    elif current_qual_section == 'essential':
                        essential_items.extend([clean_text(li.get_text()) for li in items])
                        seen_first_ul = True
                    elif current_qual_section == 'desired':
                        desired_items.extend([clean_text(li.get_text()) for li in items])
                elif sibling.name == 'br':
                    # Just skip <br> elements
                    pass
            
            job.job_posting.qualifications.essential = essential_items
            job.job_posting.qualifications.desired = desired_items
        
        # Extract Duties
        duties_p = main_div.find('span', class_='emphasis', string=re.compile(r'Duties:', re.IGNORECASE))
        if duties_p:
            # Get the parent paragraph
            duties_p = duties_p.find_parent('p')
            duties_items = []
            
            # First check for <ul> siblings (most common structure)
            for sibling in duties_p.find_next_siblings():
                if sibling.name == 'ul':
                    items = sibling.find_all('li')
                    duties_items.extend([clean_text(li.get_text()) for li in items])
                elif sibling.name == 'p' and sibling.find('span', class_='emphasis'):
                    # Stop at next section
                    break
                elif sibling.name in ['h3', 'h2']:
                    # Stop at next major section
                    break
            
            # If we found items in <ul>, use them
            if duties_items:
                job.job_posting.duties.items = duties_items
            else:
                # Fallback: try to extract from paragraph content split by <br>
                duties_html = duties_p.decode_contents() if hasattr(duties_p, 'decode_contents') else str(duties_p)
                # Remove the "Duties:" label and span tags
                duties_html = re.sub(r'<span[^>]*>Duties:</span>\s*<br/?>\s*', '', duties_html, flags=re.IGNORECASE)
                duties_soup = BeautifulSoup(duties_html, 'html.parser')
                duties_text = clean_text(duties_soup.get_text())
                
                # Split by <br> or periods for multiple duties
                if duties_text:
                    # Try to split intelligently
                    duties_parts = re.split(r'<br\s*/?>', duties_html)
                    duties_items = []
                    for part in duties_parts:
                        part_text = clean_text(BeautifulSoup(part, 'html.parser').get_text())
                        if part_text and len(part_text) > 10:
                            duties_items.append(part_text)
                    
                    # If we only got one item, store as intro
                    if len(duties_items) == 1:
                        job.job_posting.duties.intro = duties_items[0]
                    else:
                        # First item as intro, rest as items
                        if duties_items:
                            job.job_posting.duties.intro = duties_items[0]
                            if len(duties_items) > 1:
                                job.job_posting.duties.items = duties_items[1:]
        
        # Extract application form link if present (in position overview section)
        app_form_link = main_div.find('a', href=re.compile(r'application.*form', re.IGNORECASE))
        if app_form_link:
            link_text = clean_text(app_form_link.get_text())
            link_url = app_form_link.get('href', '')
            if link_text and link_url:
                job.job_posting.benefits.summary_paragraph = f"{link_text}"
                # Also store in application instructions
                job.job_posting.application_instructions.requires_application_form = True
                job.job_posting.application_instructions.application_form_link_text = link_text
                job.job_posting.application_instructions.application_form_url = link_url
        
        # Extract "Apply to" section
        apply_h3 = main_div.find('h3', string=re.compile(r'Apply to:', re.IGNORECASE))
        if apply_h3:
            # Get the div after h3
            apply_div = apply_h3.find_next_sibling('div')
            if apply_div:
                div_text = apply_div.get_text()
                lines = [clean_text(line) for line in div_text.split('\n') if clean_text(line)]
                
                apply_to = MANApplyToBlock()
                
                # Parse lines
                for i, line in enumerate(lines):
                    if line.startswith('Advertisement #'):
                        apply_to.advertisement_number = line.replace('Advertisement #', '').strip()
                    elif i < len(lines) - 1:  # Not the last line
                        if not apply_to.unit:
                            apply_to.unit = line
                        elif not apply_to.branch:
                            apply_to.branch = line
                        elif 'Phone:' in line:
                            apply_to.phone = line.replace('Phone:', '').strip()
                        elif 'Fax:' in line:
                            apply_to.fax = line.replace('Fax:', '').strip()
                        elif 'Email:' in line or '@' in line:
                            # Extract email
                            email_match = re.search(r'[\w\.-]+@[\w\.-]+', line)
                            if email_match:
                                apply_to.email = email_match.group(0)
                        elif re.search(r'[A-Z]\d[A-Z]\s*\d[A-Z]\d', line):  # Postal code
                            # This line and previous lines are address
                            # Back-track to find address lines
                            addr_start = max(0, i - 2)
                            apply_to.address_lines = lines[addr_start:i+1]
                
                job.job_posting.application_instructions.apply_to_block = apply_to
        
        # Extract instruction paragraphs (emphasis paragraphs after Apply to)
        instruction_paragraphs = []
        seen_apply_h3 = False
        for elem in main_div.find_all(['h3', 'p']):
            if elem.name == 'h3' and 'Apply to' in elem.get_text():
                seen_apply_h3 = True
                continue
            
            if seen_apply_h3 and elem.name == 'p':
                if elem.get('class') and 'emphasis' in elem.get('class'):
                    text = clean_text(elem.get_text())
                    if text and text != '_':  # Skip the final underscore
                        instruction_paragraphs.append(text)
        
        if instruction_paragraphs:
            job.job_posting.application_instructions.instruction_text = instruction_paragraphs
            
            # Parse specific instruction types
            for para in instruction_paragraphs:
                if 'accommodation' in para.lower():
                    job.job_posting.application_instructions.accommodation_text = para
                elif 'grievance' in para.lower() or 'grieved' in para.lower():
                    job.job_posting.application_instructions.grievance_notice = para
                elif 'thank' in para.lower() and 'contact' in para.lower():
                    job.job_posting.application_instructions.contact_note = para
        
        # Set the job URL
        job.job_posting.source.url = f"https://jobsearch.gov.mb.ca/search.action?ID={job_id}"
        
        return job
    
    except Exception as e:
        print(f"Error parsing job details: {e}")
        import traceback
        traceback.print_exc()
        return None
