"""
Data models for Manitoba Government Jobs
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class MANSalary:
    """Salary information"""
    raw_text: Optional[str] = None
    classification_code: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    frequency: str = "per year"
    currency: str = "CAD"


@dataclass
class MANMetadata:
    """Job metadata"""
    job_title: Optional[str] = None
    classification_title: Optional[str] = None
    classification_code: Optional[str] = None
    employment_types: List[str] = field(default_factory=list)
    departments: List[str] = field(default_factory=list)
    divisions: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    advertisement_number: Optional[str] = None
    salary: MANSalary = field(default_factory=MANSalary)
    closing_date: Optional[str] = None
    closing_time: Optional[str] = None


@dataclass
class MANEmploymentEquity:
    """Employment equity information"""
    intro_paragraph: Optional[str] = None
    equity_factor_statement: Optional[str] = None
    designated_groups: List[str] = field(default_factory=list)


@dataclass
class MANCompetitionNotes:
    """Competition-related notes"""
    eligibility_list_text: Optional[str] = None
    classification_flex_text: Optional[str] = None
    usage_text: Optional[str] = None


@dataclass
class MANPositionOverview:
    """Position overview"""
    summary_paragraphs: List[str] = field(default_factory=list)


@dataclass
class MANBenefits:
    """Benefits information"""
    summary_paragraph: Optional[str] = None
    benefit_items: List[str] = field(default_factory=list)


@dataclass
class MANConditionsOfEmployment:
    """Conditions of employment"""
    heading: str = "Conditions of Employment"
    items: List[str] = field(default_factory=list)


@dataclass
class MANQualifications:
    """Qualifications"""
    heading: str = "Qualifications"
    essential: List[str] = field(default_factory=list)
    desired: List[str] = field(default_factory=list)
    equivalency_text: Optional[str] = None


@dataclass
class MANDuties:
    """Duties"""
    heading: str = "Duties"
    intro: Optional[str] = None
    items: List[str] = field(default_factory=list)


@dataclass
class MANApplyToBlock:
    """Application contact information"""
    advertisement_number: Optional[str] = None
    unit: Optional[str] = None
    branch: Optional[str] = None
    address_lines: List[str] = field(default_factory=list)
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None


@dataclass
class MANApplicationInstructions:
    """Application instructions"""
    apply_to_block: MANApplyToBlock = field(default_factory=MANApplyToBlock)
    requires_application_form: bool = False
    application_form_link_text: Optional[str] = None
    application_form_url: Optional[str] = None
    instruction_text: List[str] = field(default_factory=list)
    accommodation_text: Optional[str] = None
    grievance_notice: Optional[str] = None
    contact_note: Optional[str] = None


@dataclass
class MANSource:
    """Source information"""
    jurisdiction: str = "Manitoba"
    job_board: str = "Government of Manitoba Careers"
    url: Optional[str] = None


@dataclass
class MANJobPosting:
    """Main job posting data structure"""
    search_keyword: Optional[str] = None
    source: MANSource = field(default_factory=MANSource)
    metadata: MANMetadata = field(default_factory=MANMetadata)
    employment_equity: MANEmploymentEquity = field(default_factory=MANEmploymentEquity)
    competition_notes: MANCompetitionNotes = field(default_factory=MANCompetitionNotes)
    position_overview: MANPositionOverview = field(default_factory=MANPositionOverview)
    benefits: MANBenefits = field(default_factory=MANBenefits)
    conditions_of_employment: MANConditionsOfEmployment = field(default_factory=MANConditionsOfEmployment)
    qualifications: MANQualifications = field(default_factory=MANQualifications)
    duties: MANDuties = field(default_factory=MANDuties)
    application_instructions: MANApplicationInstructions = field(default_factory=MANApplicationInstructions)


@dataclass
class MANScrapingMetadata:
    """Scraping metadata"""
    job_id: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    matched_keyword: Optional[str] = None
    match_score: Optional[int] = None


@dataclass
class MANJob:
    """Complete Manitoba job data"""
    job_posting: MANJobPosting = field(default_factory=MANJobPosting)
    scraping_metadata: MANScrapingMetadata = field(default_factory=MANScrapingMetadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
