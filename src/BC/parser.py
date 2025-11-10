"""
BC Job Posting Parser

Parses HTML content from BC Public Service job postings and extracts structured data.
"""

import re
from typing import Optional, List
from bs4 import BeautifulSoup
from datetime import datetime

from .models import (
    BCJob, BCJobPosting, BCSource, BCMetadata, BCSalary,
    BCJobSummary, BCAboutSection, BCPositionRequirements, BCEducationExperience,
    BCApplicationInstructions, BCApplicationRequirements, BCHRContact,
    BCSubmissionMethod, BCTechnicalHelpContact, BCWorkingForBCPS,
    BCIndigenousAdvisoryService, BCAttachments, BCAttachmentFile, BCScrapingMetadata
)


def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_field_value(soup: BeautifulSoup, field_id: str) -> Optional[str]:
    """Extract value from a form-group field by its ID"""
    element = soup.find('div', {'id': field_id})
    if element:
        text = element.get_text(strip=True)
        text = text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
        return text if text else None
    return None


def parse_salary(salary_text: Optional[str]) -> Optional[BCSalary]:
    """Parse salary string into structured format"""
    if not salary_text:
        return None
    
    pattern = r'\$?([\d,]+\.?\d*)\s*(?:to|-)\s*\$?([\d,]+\.?\d*)\s*(per\s+\w+)?'
    match = re.search(pattern, salary_text, re.IGNORECASE)
    
    if match:
        min_amt = float(match.group(1).replace(',', ''))
        max_amt = float(match.group(2).replace(',', ''))
        frequency = match.group(3) if match.group(3) else "per annum"
        
        tma_match = re.search(r'temporary market adjustment[:\s]*\$?([\d,]+\.?\d*%?)', salary_text, re.IGNORECASE)
        tma = tma_match.group(1) if tma_match else None
        
        return BCSalary(
            raw_text=salary_text,
            min_amount=min_amt,
            max_amount=max_amt,
            frequency=frequency.strip(),
            currency="CAD",
            temporary_market_adjustment=tma
        )
    
    return BCSalary(
        raw_text=salary_text,
        min_amount=None,
        max_amount=None,
        frequency=None,
        currency="CAD",
        temporary_market_adjustment=None
    )


def parse_locations(location_element) -> List[str]:
    """Parse location element into list of locations"""
    if not location_element:
        return []
    
    locations = []
    for text in location_element.stripped_strings:
        text = clean_text(text)
        if text:
            locations.append(text)
    
    return locations


def parse_job_summary(soup: BeautifulSoup) -> BCJobSummary:
    """Parse the job summary section"""
    summary_div = soup.find('div', {'id': 'job_details_ats_requisition_description'})
    
    if not summary_div:
        return BCJobSummary(
            about_organization=BCAboutSection(heading=None, body=[]),
            about_business_unit=BCAboutSection(heading=None, body=[]),
            about_role=BCAboutSection(heading=None, body=[]),
            special_conditions=[],
            eligibility_list_note=None
        )
    
    paragraphs = []
    for elem in summary_div.find_all(['p', 'ul', 'ol'], recursive=True):
        if elem.name == 'p':
            text = clean_text(elem.get_text())
            if text and text not in paragraphs:
                paragraphs.append(text)
        elif elem.name in ['ul', 'ol']:
            items = []
            for li in elem.find_all('li', recursive=False):
                item_text = clean_text(li.get_text())
                if item_text:
                    items.append(item_text)
            
            if items:
                list_text = '\n'.join(f"• {item}" for item in items)
                if list_text and list_text not in paragraphs:
                    paragraphs.append(list_text)
    
    return BCJobSummary(
        about_organization=BCAboutSection(heading=None, body=[]),
        about_business_unit=BCAboutSection(heading=None, body=[]),
        about_role=BCAboutSection(
            heading="Job Description",
            body=paragraphs
        ),
        special_conditions=[],
        eligibility_list_note=None
    )


def parse_position_requirements(soup: BeautifulSoup) -> BCPositionRequirements:
    """Parse position requirements from job summary"""
    summary_div = soup.find('div', {'id': 'job_details_ats_requisition_description'})
    
    if not summary_div:
        return BCPositionRequirements(
            heading="Position requirements",
            education_and_experience=BCEducationExperience(
                required_paths=[],
                equivalency_statement=None,
                recent_experience_note=None
            ),
            required_experience_bullets=[],
            preferred_experience_bullets=[]
        )
    
    required_bullets = []
    preferred_bullets = []
    in_preferred_section = False
    in_application_section = False
    
    # Find "Position requirements" or "Qualifications" section to limit scope
    pos_req_found = False
    app_instr_found = False
    
    for elem in summary_div.find_all(['p', 'strong', 'ul']):
        elem_text = clean_text(elem.get_text()).lower()
        
        # Track section changes
        if elem.name in ['p', 'strong']:
            # Check if we've entered application instructions section
            if 'application instruction' in elem_text:
                in_application_section = True
                app_instr_found = True
                continue
            
            # Check if we're in position requirements section
            if any(phrase in elem_text for phrase in [
                'position requirement',
                'qualifications',
                'education and experience'
            ]) and not in_application_section:
                pos_req_found = True
                in_application_section = False
                continue
            
            # If we've found app instructions, skip everything after
            if app_instr_found:
                continue
                
            # Check for preferred/nice-to-have indicators
            if any(phrase in elem_text for phrase in [
                'nice to have', 
                'preferred', 
                'preference may be given',
                'preference will be given',
                'asset',
                'an asset'
            ]):
                in_preferred_section = True
                continue
            
            # Check for required/must-have indicators
            if any(phrase in elem_text for phrase in [
                'must have',
                'required',
                'qualifications',
                'education and experience'
            ]) and not in_preferred_section:
                in_preferred_section = False
                continue
        
        # Extract bullets from lists (only if we're in position requirements)
        if elem.name == 'ul' and pos_req_found and not in_application_section:
            for li in elem.find_all('li', recursive=False):
                bullet = clean_text(li.get_text())
                if bullet:
                    # Skip bullets that are clearly application instructions
                    if any(phrase in bullet.lower() for phrase in [
                        'cover letter is required',
                        'ensure your resume',
                        'applications will be accepted',
                        'application must clearly demonstrate'
                    ]):
                        continue
                    
                    if in_preferred_section:
                        preferred_bullets.append(bullet)
                    else:
                        required_bullets.append(bullet)
    
    return BCPositionRequirements(
        heading="Position requirements",
        education_and_experience=BCEducationExperience(
            required_paths=[],
            equivalency_statement=None,
            recent_experience_note=None
        ),
        required_experience_bullets=required_bullets,
        preferred_experience_bullets=preferred_bullets
    )


def parse_application_instructions(soup: BeautifulSoup) -> BCApplicationInstructions:
    """Parse application instructions"""
    summary_div = soup.find('div', {'id': 'job_details_ats_requisition_description'})
    
    submission_notes = []
    hr_name = None
    hr_title = None
    hr_email = None
    
    if summary_div:
        # Look for HR contact in the job summary
        for p in summary_div.find_all('p'):
            p_text = p.get_text()
            
            # Check for HR contact pattern: "contact [Name], [Title] at [email]"
            contact_match = re.search(
                r'contact\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([^,]+?)\s+at\s+([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})',
                p_text,
                re.IGNORECASE
            )
            if contact_match:
                hr_name = contact_match.group(1).strip()
                hr_title = contact_match.group(2).strip()
                hr_email = contact_match.group(3).strip()
    
    # Also check for "How to apply" section in the form
    apply_label = soup.find('label', string=re.compile(r'How to apply', re.IGNORECASE))
    if apply_label:
        apply_div = apply_label.find_next('div', class_='cell_input')
        if apply_div:
            for p in apply_div.find_all('p'):
                text = clean_text(p.get_text())
                if text:
                    submission_notes.append(text)
    
    return BCApplicationInstructions(
        heading="Application instructions",
        evaluation_note=None,
        requirements=BCApplicationRequirements(
            cover_letter_required=True,
            resume_details_required=True,
            other_documents=[]
        ),
        hr_contact=BCHRContact(
            name=hr_name,
            title=hr_title,
            email=hr_email
        ),
        submission_method=BCSubmissionMethod(
            system_name="BC Public Service Recruitment System",
            notes=submission_notes
        ),
        technical_help_contact=BCTechnicalHelpContact(
            email="BCPSA.Hiring.Centre@gov.bc.ca",
            notes=[]
        ),
        deadline_note="Applications will be accepted until 11:00pm Pacific Time on the closing date of the competition."
    )


def parse_attachments(soup: BeautifulSoup) -> BCAttachments:
    """Parse job attachments from Additional Information section"""
    attachments = []
    
    # Look for "Additional Information" section
    for label in soup.find_all('div', class_='col-sm-3'):
        if 'Additional Information' in label.get_text():
            # Find the next div with attachments
            attachments_div = label.find_next('div', class_='cell_input')
            if attachments_div:
                # Find all download links
                for link in attachments_div.find_all('a', onclick=re.compile(r'downloadFileValidation')):
                    filename = clean_text(link.get_text())
                    url = link.get('href', '')
                    if filename and url:
                        attachments.append(BCAttachmentFile(
                            label=filename,
                            path_or_url=url
                        ))
                break
    
    return BCAttachments(job_description_files=attachments)


def parse_working_for_bcps(soup: BeautifulSoup) -> BCWorkingForBCPS:
    """Parse Working for BC Public Service section"""
    summary_div = soup.find('div', {'id': 'job_details_ats_requisition_description'})
    
    diversity_statement = None
    flexible_work_statement = None
    indigenous_description = None
    
    if summary_div:
        for p in summary_div.find_all('p'):
            p_text = p.get_text()
            p_text_lower = p_text.lower()
            
            # Extract diversity statement
            if not diversity_statement and any(phrase in p_text_lower for phrase in [
                'diversity', 'equal opportunity', 'inclusion', 'diverse workplace'
            ]):
                diversity_statement = clean_text(p_text)
            
            # Extract flexible work statement
            if not flexible_work_statement and any(phrase in p_text_lower for phrase in [
                'flexible work', 'hybrid work', 'work-from-home', 'flexible workplace'
            ]):
                flexible_work_statement = clean_text(p_text)
            
            # Extract indigenous applicant service description
            if not indigenous_description and 'indigenous applicant' in p_text_lower:
                indigenous_description = clean_text(p_text)
    
    return BCWorkingForBCPS(
        diversity_statement=diversity_statement,
        flexible_work_statement=flexible_work_statement,
        indigenous_applicant_advisory_service=BCIndigenousAdvisoryService(
            available=True if indigenous_description else False,
            description=indigenous_description,
            contact_email=None,
            contact_phone=None
        ),
        employer_value_proposition=[]
    )


def parse_job_details(html_content: str, job_id: str, matched_keyword: str, match_score: int) -> Optional[BCJob]:
    """Parse BC job posting HTML and extract structured data"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        posting_title = extract_field_value(soup, 'job_details_ats_requisition_title')
        position_classification = extract_field_value(soup, 'job_details_ats_requisition_level_id')
        union = extract_field_value(soup, 'job_details_hua_union_name')
        work_options = extract_field_value(soup, 'job_details_f_work_options_0')
        
        location_div = soup.find('div', {'id': 'job_details_hua_location_id'})
        locations = parse_locations(location_div)
        
        salary_text = extract_field_value(soup, 'job_details_f_salary_range_0')
        close_date = extract_field_value(soup, 'job_details_f_close_date_0')
        job_type = extract_field_value(soup, 'job_details_f_job_type_displayed_on_posting_0')
        temp_end_date = extract_field_value(soup, 'job_details_f_temporary_end_date_0')
        ministry_org = extract_field_value(soup, 'job_details_hua_org_level_id')
        ministry_branch = extract_field_value(soup, 'job_details_f_ministry_branch__division_0')
        job_category = extract_field_value(soup, 'job_details_ats_requisition_category_id')
        
        salary = parse_salary(salary_text)
        
        org_name = "BC Public Service"
        if ministry_org and '->' in ministry_org:
            parts = ministry_org.split('->')
            if len(parts) > 1:
                org_name = clean_text(parts[1])
        
        metadata = BCMetadata(
            posting_title=posting_title,
            posting_id=job_id,
            job_title=posting_title,
            position_classification=position_classification,
            classification_code=position_classification,
            union=union,
            work_options=work_options if work_options else None,
            locations=locations,
            salary=salary,
            close_date=close_date,
            close_time="11:00 pm Pacific Time",
            job_type=job_type,
            temporary_end_date=temp_end_date if temp_end_date else None,
            ministry_organization=ministry_org,
            ministry_branch_division=ministry_branch,
            job_category=job_category
        )
        
        job_summary = parse_job_summary(soup)
        position_requirements = parse_position_requirements(soup)
        application_instructions = parse_application_instructions(soup)
        working_for_bc = parse_working_for_bcps(soup)
        attachments = parse_attachments(soup)
        
        job_posting = BCJobPosting(
            search_keyword=matched_keyword,
            source=BCSource(
                jurisdiction="British Columbia",
                job_board="BC Public Service",
                organization=org_name,
                url=f"https://bcpublicservice.hua.hrsmart.com/hr/ats/Posting/view/{job_id}"
            ),
            metadata=metadata,
            amendments=[],
            job_summary=job_summary,
            position_requirements=position_requirements,
            application_instructions=application_instructions,
            working_for_bc_public_service=working_for_bc,
            attachments=attachments
        )
        
        scraping_metadata = BCScrapingMetadata(
            job_id=job_id,
            scraped_at=datetime.now().isoformat(),
            matched_keyword=matched_keyword,
            match_score=match_score
        )
        
        return BCJob(
            job_posting=job_posting,
            scraping_metadata=scraping_metadata
        )
        
    except Exception as e:
        print(f"Error parsing job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        return None
