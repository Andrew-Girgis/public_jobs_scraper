"""
Data models for Tasmania Government Job Scraper
"""

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class TASJob:
    """Tasmania government job posting"""
    # Job identification
    job_id: str
    job_reference: Optional[str]
    job_title: str
    job_url: str
    
    # Organization
    agency: str
    
    # Location
    region: Optional[str]
    location: Optional[str]
    
    # Employment details
    award: Optional[str]  # e.g., "Tasmanian State Service Award - General Stream Band 3"
    employment_type: Optional[str]  # e.g., "Permanent, full-time"
    
    # Dates
    closing_date: str  # e.g., "Thursday 20 November, 2025 11:55 PM"
    
    # Salary
    salary: Optional[str]  # e.g., "$74,783.00 to $80,835.00 per annum"
    
    # Job content
    summary: Optional[str]  # Job description from search results
    description_html: str  # Full HTML description from job page
    
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
class TASScrapingMetadata:
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
