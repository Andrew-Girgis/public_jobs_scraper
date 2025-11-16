"""
Data models for Queensland Government Job Scraper
"""

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class QLDJob:
    """Queensland government job posting"""
    # Job identification
    job_id: str
    job_reference: Optional[str]
    job_title: str
    job_url: str
    
    # Organization
    organization: str  # e.g., "Queensland Health", "Crime and Corruption Commission"
    department: Optional[str]  # For sub-departments
    
    # Location
    location: Optional[str]  # e.g., "Brisbane Inner City", "Mackay region"
    
    # Employment details
    position_status: Optional[str]  # e.g., "Permanent", "Contract", "Fixed Term Temporary"
    position_type: Optional[str]  # e.g., "Full-time", "Flexible full-time", "Part-time"
    occupational_group: Optional[str]  # e.g., "Administration", "IT & Telecommunications"
    classification: Optional[str]  # e.g., "AO7", "AO6", "Nurse Grade 6 (1)"
    
    # Dates
    closing_date: str  # e.g., "26-Nov-2025"
    date_posted: Optional[str]
    
    # Salary Information
    salary_yearly: Optional[str]  # e.g., "$119802 - $127942 (yearly)"
    salary_fortnightly: Optional[str]  # e.g., "$4592.00 - $4904.00 (fortnightly)"
    total_remuneration: Optional[str]  # e.g., "$136889 up to $146190 (total remuneration)"
    
    # Job content
    summary: Optional[str]  # Job description from search results
    description_html: str  # Full HTML description from job page
    
    # Contact information
    contact_person: Optional[str]
    contact_details: Optional[str]
    
    # Matching metadata
    search_keyword: str
    matched_keyword: str
    match_score: int
    
    # Scraping metadata
    scraped_at: str  # ISO format timestamp
    scraper_version: str
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class QLDScrapingMetadata:
    """Metadata about the scraping session"""
    scrape_date: str
    keywords_searched: List[str]
    total_jobs_found: int
    jobs_scraped: int
    jobs_filtered: int
    errors: List[str]
    duration_seconds: float
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)
