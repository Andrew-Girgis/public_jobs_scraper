"""
Data models for Victoria (Australia) job scraper
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class VICJob:
    """Victoria government job posting data structure"""
    
    # Identification
    job_id: str
    job_reference: str
    job_title: str
    job_url: str
    
    # Organization
    organization: str
    
    # Location
    location: str
    
    # Employment Details
    work_type: str  # e.g., "Ongoing - Full-time"
    grade: str  # e.g., "VPS 5"
    occupation: str  # e.g., "IT and telecommunications"
    
    # Dates
    posted_date: str
    closing_date: str
    
    # Description
    summary: str
    description_html: str
    
    # Optional fields
    salary: Optional[str] = None
    logo_url: Optional[str] = None
    
    # Matching metadata
    search_keyword: str = ""
    matched_keyword: Optional[str] = None
    match_score: int = 0
    
    # Scraping metadata
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    scraper_version: str = "1.0"


@dataclass
class VICScrapingMetadata:
    """Metadata for the scraping session"""
    
    scrape_date: str
    keywords_searched: int
    total_jobs_found: int
    jobs_scraped: int
    jobs_filtered: int
    errors: int
    duration_seconds: float
