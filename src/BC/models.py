"""
Data models for BC Public Service job postings
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class BCSource:
    """Source information for BC job posting"""
    jurisdiction: str = "British Columbia"
    job_board: str = "BC Public Service"
    organization: Optional[str] = None
    url: Optional[str] = None


@dataclass
class BCSalary:
    """Salary information"""
    raw_text: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    frequency: Optional[str] = None  # e.g., "per annum"
    currency: str = "CAD"
    temporary_market_adjustment: Optional[str] = None  # e.g., "9.9%"


@dataclass
class BCMetadata:
    """Job metadata"""
    posting_title: Optional[str] = None
    posting_id: Optional[str] = None  # e.g., "121578"
    job_title: Optional[str] = None
    position_classification: Optional[str] = None  # e.g., "Administrative Officer R18"
    classification_code: Optional[str] = None  # e.g., "ADMN O 18R"
    union: Optional[str] = None
    work_options: Optional[str] = None  # e.g., "Hybrid"
    locations: List[str] = field(default_factory=list)
    salary: BCSalary = field(default_factory=BCSalary)
    close_date: Optional[str] = None
    close_time: str = "11:00 pm Pacific Time"
    job_type: Optional[str] = None  # e.g., "Regular Full Time"
    temporary_end_date: Optional[str] = None
    ministry_organization: Optional[str] = None
    ministry_branch_division: Optional[str] = None
    job_category: Optional[str] = None


@dataclass
class BCAmendment:
    """Job posting amendment"""
    date: Optional[str] = None
    description: Optional[str] = None


@dataclass
class BCAboutSection:
    """Generic about section with heading and body"""
    heading: Optional[str] = None
    body: List[str] = field(default_factory=list)


@dataclass
class BCJobSummary:
    """Job summary information"""
    about_organization: BCAboutSection = field(default_factory=BCAboutSection)
    about_business_unit: BCAboutSection = field(default_factory=BCAboutSection)
    about_role: BCAboutSection = field(default_factory=BCAboutSection)
    special_conditions: List[str] = field(default_factory=list)
    eligibility_list_note: Optional[str] = None


@dataclass
class BCEducationPath:
    """Single education/experience requirement path"""
    education: Optional[str] = None
    experience_years: Optional[int] = None


@dataclass
class BCEducationExperience:
    """Education and experience requirements"""
    required_paths: List[BCEducationPath] = field(default_factory=list)
    equivalency_statement: Optional[str] = None
    recent_experience_note: Optional[str] = None


@dataclass
class BCPositionRequirements:
    """Position requirements section"""
    heading: str = "Position requirements"
    education_and_experience: BCEducationExperience = field(default_factory=BCEducationExperience)
    required_experience_bullets: List[str] = field(default_factory=list)
    preferred_experience_bullets: List[str] = field(default_factory=list)


@dataclass
class BCApplicationRequirements:
    """Application submission requirements"""
    cover_letter_required: Optional[bool] = None
    resume_details_required: bool = True
    other_documents: List[str] = field(default_factory=list)


@dataclass
class BCHRContact:
    """HR contact information"""
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None


@dataclass
class BCSubmissionMethod:
    """Application submission method"""
    system_name: str = "BC Public Service Recruitment System"
    notes: List[str] = field(default_factory=list)


@dataclass
class BCTechnicalHelpContact:
    """Technical help contact"""
    email: str = "BCPSA.Hiring.Centre@gov.bc.ca"
    notes: List[str] = field(default_factory=list)


@dataclass
class BCApplicationInstructions:
    """Application instructions"""
    heading: str = "Application instructions"
    evaluation_note: Optional[str] = None
    requirements: BCApplicationRequirements = field(default_factory=BCApplicationRequirements)
    hr_contact: BCHRContact = field(default_factory=BCHRContact)
    submission_method: BCSubmissionMethod = field(default_factory=BCSubmissionMethod)
    technical_help_contact: BCTechnicalHelpContact = field(default_factory=BCTechnicalHelpContact)
    deadline_note: str = "Applications will be accepted until 11:00pm Pacific Time on the closing date of the competition."


@dataclass
class BCIndigenousAdvisoryService:
    """Indigenous Applicant Advisory Service"""
    available: bool = True
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


@dataclass
class BCWorkingForBCPS:
    """Working for BC Public Service section"""
    diversity_statement: Optional[str] = None
    flexible_work_statement: Optional[str] = None
    indigenous_applicant_advisory_service: BCIndigenousAdvisoryService = field(
        default_factory=BCIndigenousAdvisoryService
    )
    employer_value_proposition: List[str] = field(default_factory=list)


@dataclass
class BCAttachmentFile:
    """Attachment file information"""
    label: Optional[str] = None
    path_or_url: Optional[str] = None


@dataclass
class BCAttachments:
    """Job attachments"""
    job_description_files: List[BCAttachmentFile] = field(default_factory=list)


@dataclass
class BCJobPosting:
    """Complete BC job posting"""
    search_keyword: Optional[str] = None
    source: BCSource = field(default_factory=BCSource)
    metadata: BCMetadata = field(default_factory=BCMetadata)
    amendments: List[BCAmendment] = field(default_factory=list)
    job_summary: BCJobSummary = field(default_factory=BCJobSummary)
    position_requirements: BCPositionRequirements = field(default_factory=BCPositionRequirements)
    application_instructions: BCApplicationInstructions = field(default_factory=BCApplicationInstructions)
    working_for_bc_public_service: BCWorkingForBCPS = field(default_factory=BCWorkingForBCPS)
    attachments: BCAttachments = field(default_factory=BCAttachments)


@dataclass
class BCScrapingMetadata:
    """Scraping metadata"""
    job_id: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    matched_keyword: Optional[str] = None
    match_score: Optional[int] = None


@dataclass
class BCJob:
    """Complete BC job with metadata"""
    job_posting: BCJobPosting = field(default_factory=BCJobPosting)
    scraping_metadata: BCScrapingMetadata = field(default_factory=BCScrapingMetadata)
