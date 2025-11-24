"""
Data models for NSW Job Scraper
"""

from dataclasses import dataclass, asdict
from typing import Optional, List


@dataclass
class NSWJob:
    """Represents a New South Wales government job posting."""
    
    # Job identification
    job_id: str
    job_reference: str
    job_title: str
    job_url: str
    
    # Organization
    organization: Optional[str] = None
    
    # Location
    location: Optional[str] = None
    
    # Job details
    job_category: Optional[str] = None
    work_type: Optional[str] = None
    
    # Dates
    closing_date: Optional[str] = None
    
    # Salary
    salary_range: Optional[str] = None
    
    # Job content
    summary: Optional[str] = None
    description_html: Optional[str] = None
    
    # Scraping metadata
    search_keyword: str = ""
    matched_keyword: str = ""
    match_score: int = 0
    scraped_at: str = ""
    scraper_version: str = "1.0"
    
    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class NSWScrapingMetadata:
    """Metadata about a scraping session."""
    
    scrape_date: str
    keywords_searched: List[str]
    total_jobs_found: int
    jobs_scraped: int
    jobs_filtered: int
    errors: List[str]
    duration_seconds: float
    
    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)
