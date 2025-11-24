"""
Data models for WA Job Scraper
"""

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class WAJob:
    """Represents a job posting from WA Government"""
    job_id: str  # Derived from AdvertID in URL
    position_number: str
    job_title: str
    job_url: str
    agency: str
    branch: Optional[str]
    location: str
    classification: str
    posting_date: str
    closing_date: str
    division_name: Optional[str]
    job_type: Optional[str]
    salary: Optional[str]
    description_html: str
    description_text: Optional[str]
    attachments: List[dict]  # List of {"name": str, "url": str}
    search_keyword: str
    matched_keyword: str
    match_score: float
    scraped_at: str
    scraper_version: str
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class WAScrapingMetadata:
    """Metadata about a scraping session"""
    scrape_date: str
    keywords_searched: int
    total_jobs_found: int
    jobs_scraped: int
    jobs_filtered: int
    errors: int
    duration_seconds: float
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)
