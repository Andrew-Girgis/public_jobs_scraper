"""
Government of Canada Job Posting Data Models

This module defines the unified data structure for GC Jobs postings.
It handles three different page structures:
- Structure 1: New-style layout (e.g., Junior Data Analyst)
- Structure 2: Classic layout (e.g., Development Program Officer)
- External Redirect: Links to external job boards

All three structures are normalized into a single GocJob model.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, date


@dataclass
class ContactInfo:
    """Contact information for a hiring manager or HR representative."""
    name: str = ""
    role: str = ""
    email: str = ""
    phone: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class QualificationBlock:
    """
    A single qualification category (education, experience, etc.)
    stored as a list of requirement strings.
    """
    education: List[str] = field(default_factory=list)
    experience: List[str] = field(default_factory=list)
    knowledge: List[str] = field(default_factory=list)
    abilities: List[str] = field(default_factory=list)
    competencies: List[str] = field(default_factory=list)
    personal_suitability: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Qualifications:
    """Essential and asset qualifications for a job posting."""
    essential: QualificationBlock = field(default_factory=QualificationBlock)
    asset: QualificationBlock = field(default_factory=QualificationBlock)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'essential': self.essential.to_dict(),
            'asset': self.asset.to_dict()
        }


@dataclass
class Sections:
    """
    Text content sections from the job posting.
    These are free-form text blocks describing various aspects of the job.
    """
    work_environment: str = ""
    duties: str = ""
    important_messages: str = ""
    operational_requirements: str = ""
    conditions_of_employment: str = ""
    how_to_apply: str = ""
    equity_diversity_inclusion: str = ""
    our_commitment: str = ""
    preference: str = ""
    organization_information: str = ""
    other_information: str = ""
    intent_of_process: str = ""
    reference_number: str = ""
    selection_process_number: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Contact:
    """Contact information section containing one or more contacts."""
    contacts: List[ContactInfo] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'contacts': [c.to_dict() for c in self.contacts]
        }


@dataclass
class JobDetails:
    """
    Detailed information about a job posting including sections,
    qualifications, and contact information.
    """
    sections: Sections = field(default_factory=Sections)
    qualifications: Qualifications = field(default_factory=Qualifications)
    contact: Contact = field(default_factory=Contact)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'sections': self.sections.to_dict(),
            'qualifications': self.qualifications.to_dict(),
            'contact': self.contact.to_dict()
        }


@dataclass
class GocJob:
    """
    Unified model for a Government of Canada job posting.
    
    This model represents job postings from three different page structures:
    - structure_1: New-style layout with modern navigation
    - structure_2: Classic layout with traditional sections
    - external_redirect: Link to external job board
    
    All three structures are normalized into this common format for consistent
    storage and analysis.
    
    Attributes:
        poster_id: Unique identifier for the job posting
        url: Full URL to the job posting on GC Jobs
        title: Job title
        department: Government department name
        branch: Department branch or division
        city: City where job is located
        province: Province where job is located
        location_raw: Raw location string from the posting
        classification_group: Job classification group (e.g., "EC", "PM")
        classification_level: Job classification level (e.g., "01", "02")
        classification_raw: Raw classification string (e.g., "EC-02")
        closing_date: Application deadline (ISO date)
        closing_time_raw: Raw closing time string with timezone
        date_modified: Date the posting was last modified
        salary_min: Minimum salary in dollars
        salary_max: Maximum salary in dollars
        salary_raw: Raw salary string from the posting
        who_can_apply: Eligibility criteria text
        employment_types: Types of employment (Acting, Indeterminate, etc.)
        positions_to_fill: Number of positions available
        language_requirements_raw: Language requirement text
        is_external_link: Whether this is an external redirect
        external_redirect_url: URL to external job board (if applicable)
        external_job_title: Job title on external site (if applicable)
        search_title: Search query that found this job
        search_type: Type of search (e.g., "production", "dev")
        scraped_at: Timestamp when the job was scraped
        structure_type: Page structure type (structure_1, structure_2, or external_redirect)
        details: Nested object containing sections, qualifications, and contact info
    """
    
    # Core identification
    poster_id: str
    url: str
    
    # Job basics
    title: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    
    # Location
    city: Optional[str] = None
    province: Optional[str] = None
    location_raw: Optional[str] = None
    
    # Classification
    classification_group: Optional[str] = None
    classification_level: Optional[str] = None
    classification_raw: Optional[str] = None
    
    # Dates
    closing_date: Optional[date] = None
    closing_time_raw: Optional[str] = None
    date_modified: Optional[date] = None
    
    # Salary
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_raw: Optional[str] = None
    
    # Application details
    who_can_apply: Optional[str] = None
    employment_types: Optional[str] = None
    positions_to_fill: Optional[int] = None
    
    # Language
    language_requirements_raw: Optional[str] = None
    
    # External link info
    is_external_link: bool = False
    external_redirect_url: Optional[str] = None
    external_job_title: Optional[str] = None
    
    # Scraping metadata
    search_title: str = ""
    search_type: str = "production"
    scraped_at: Optional[datetime] = None
    structure_type: str = ""
    
    # Detailed information
    details: JobDetails = field(default_factory=JobDetails)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the GocJob instance to a dictionary suitable for JSON serialization.
        
        Handles conversion of date/datetime objects to ISO format strings.
        
        Returns:
            Dictionary representation of the job posting
        """
        data = {
            'poster_id': self.poster_id,
            'url': self.url,
            'title': self.title,
            'department': self.department,
            'branch': self.branch,
            'city': self.city,
            'province': self.province,
            'location_raw': self.location_raw,
            'classification_group': self.classification_group,
            'classification_level': self.classification_level,
            'classification_raw': self.classification_raw,
            'closing_date': self.closing_date.isoformat() if self.closing_date else None,
            'closing_time_raw': self.closing_time_raw,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'salary_raw': self.salary_raw,
            'who_can_apply': self.who_can_apply,
            'employment_types': self.employment_types,
            'positions_to_fill': self.positions_to_fill,
            'language_requirements_raw': self.language_requirements_raw,
            'is_external_link': self.is_external_link,
            'external_redirect_url': self.external_redirect_url,
            'external_job_title': self.external_job_title,
            'search_title': self.search_title,
            'search_type': self.search_type,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'structure_type': self.structure_type,
            'details': self.details.to_dict()
        }
        return data
