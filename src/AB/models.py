"""
Data models for Alberta Public Service job postings
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class ABSource:
    """Source information for Alberta job posting"""
    jurisdiction: str = "Alberta"
    job_board: str = "Alberta Public Service Careers"
    company: str = "Government of Alberta"
    url: Optional[str] = None


@dataclass
class ABHeader:
    """Job posting header information"""
    job_title: Optional[str] = None
    posting_date: Optional[str] = None
    location_line: Optional[str] = None
    company_line: str = "Government of Alberta"


@dataclass
class ABSalary:
    """Salary information"""
    raw_text: Optional[str] = None
    biweekly_min: Optional[float] = None
    biweekly_max: Optional[float] = None
    annual_min: Optional[float] = None
    annual_max: Optional[float] = None
    currency: str = "CAD"
    primary_frequency: Optional[str] = None  # e.g., "bi-weekly"


@dataclass
class ABJobInformation:
    """Job information section"""
    job_title: Optional[str] = None
    job_requisition_id: Optional[str] = None
    ministry: Optional[str] = None
    location: Optional[str] = None
    full_or_part_time: Optional[str] = None
    hours_of_work: Optional[str] = None
    permanent_or_temporary: Optional[str] = None
    scope: Optional[str] = None
    closing_date: Optional[str] = None
    classification: Optional[str] = None
    salary: ABSalary = field(default_factory=ABSalary)


@dataclass
class ABDiversityInclusion:
    """Diversity and inclusion statement"""
    statement: Optional[str] = None
    policy_url: str = "https://www.alberta.ca/diversity-inclusion-policy.aspx"


@dataclass
class ABMinistryOverview:
    """Ministry overview section"""
    heading: Optional[str] = None
    body: List[str] = field(default_factory=list)


@dataclass
class ABResponsibilityGroup:
    """Group of responsibilities"""
    heading: Optional[str] = None
    items: List[str] = field(default_factory=list)


@dataclass
class ABRoleResponsibilities:
    """Role responsibilities section"""
    heading: str = "Role Responsibilities"
    tagline: Optional[str] = None
    intro_paragraphs: List[str] = field(default_factory=list)
    responsibility_groups: List[ABResponsibilityGroup] = field(default_factory=list)
    job_description_link_text: Optional[str] = None
    job_description_url: Optional[str] = None


@dataclass
class ABAPSCompetencies:
    """APS Competencies section"""
    heading: str = "APS Competencies"
    description: Optional[str] = None
    competencies_url: str = "https://www.alberta.ca/system/files/custom_downloaded_images/psc-alberta-public-service-competency-model.pdf"
    items: List[str] = field(default_factory=list)


@dataclass
class ABRequiredQualifications:
    """Required qualifications"""
    education: List[str] = field(default_factory=list)
    experience: List[str] = field(default_factory=list)
    other: List[str] = field(default_factory=list)


@dataclass
class ABEquivalency:
    """Equivalency information"""
    text: Optional[str] = None
    rules: List[str] = field(default_factory=list)


@dataclass
class ABAssets:
    """Asset qualifications"""
    heading: str = "Assets"
    items: List[str] = field(default_factory=list)


@dataclass
class ABQualifications:
    """Qualifications section"""
    heading: str = "Qualifications"
    required: ABRequiredQualifications = field(default_factory=ABRequiredQualifications)
    equivalency: ABEquivalency = field(default_factory=ABEquivalency)
    assets: ABAssets = field(default_factory=ABAssets)
    minimum_recruitment_standards_url: str = "https://www.alberta.ca/alberta-public-service-minimum-recruitment-standards"


@dataclass
class ABResourceLink:
    """Resource link"""
    label: Optional[str] = None
    url: Optional[str] = None


@dataclass
class ABNotes:
    """Notes section"""
    heading: str = "Notes"
    employment_term: Optional[str] = None
    location_reminder: Optional[str] = None
    assessment_info: List[str] = field(default_factory=list)
    security_screening: List[str] = field(default_factory=list)
    reuse_competition_note: List[str] = field(default_factory=list)
    costs_note: List[str] = field(default_factory=list)
    benefits_and_resources_links: List[ABResourceLink] = field(default_factory=list)


@dataclass
class ABIQASRecommendation:
    """IQAS recommendation for international credentials"""
    recommended: bool = True
    iqas_url: str = "https://www.alberta.ca/international-qualifications-assessment.aspx"
    alliance_url: str = "https://canalliance.org/en/default.html"


@dataclass
class ABHowToApply:
    """How to apply section"""
    heading: str = "How To Apply"
    instructions: List[str] = field(default_factory=list)
    job_application_resources_url: str = "https://www.alberta.ca/job-application-resources#before"
    recruitment_principles_url: str = "https://www.alberta.ca/recruitment-principles"
    iqas_recommendation: ABIQASRecommendation = field(default_factory=ABIQASRecommendation)


@dataclass
class ABContactInfo:
    """Contact information"""
    name: Optional[str] = None
    email: Optional[str] = None


@dataclass
class ABClosingStatement:
    """Closing statement section"""
    reuse_competition_note: Optional[str] = None
    thanks_and_screening_note: Optional[str] = None
    contact: ABContactInfo = field(default_factory=ABContactInfo)
    accommodation_note: Optional[str] = None


@dataclass
class ABJobPosting:
    """Complete Alberta job posting"""
    search_keyword: Optional[str] = None
    source: ABSource = field(default_factory=ABSource)
    header: ABHeader = field(default_factory=ABHeader)
    job_information: ABJobInformation = field(default_factory=ABJobInformation)
    diversity_and_inclusion: ABDiversityInclusion = field(default_factory=ABDiversityInclusion)
    ministry_overview: ABMinistryOverview = field(default_factory=ABMinistryOverview)
    role_responsibilities: ABRoleResponsibilities = field(default_factory=ABRoleResponsibilities)
    aps_competencies: ABAPSCompetencies = field(default_factory=ABAPSCompetencies)
    qualifications: ABQualifications = field(default_factory=ABQualifications)
    notes: ABNotes = field(default_factory=ABNotes)
    how_to_apply: ABHowToApply = field(default_factory=ABHowToApply)
    closing_statement: ABClosingStatement = field(default_factory=ABClosingStatement)


@dataclass
class ABScrapingMetadata:
    """Scraping metadata"""
    job_id: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    matched_keyword: Optional[str] = None
    match_score: Optional[int] = None


@dataclass
class ABJob:
    """Complete Alberta job with metadata"""
    job_posting: ABJobPosting = field(default_factory=ABJobPosting)
    scraping_metadata: ABScrapingMetadata = field(default_factory=ABScrapingMetadata)
