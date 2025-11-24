"""
Data models for SA Job Scraper
"""

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class SAJob:
    """Represents a job posting from SA Government"""
    job_id: str  # Derived from AdvertID in URL
    reference_number: str
    job_title: str
    job_url: str
    agency: str
    location: str
    posting_date: str
    job_status: Optional[str]  # e.g., "Long Term Contract", "Permanent"
    eligibility: Optional[str]  # e.g., "Open to Everyone"
    closing_date: str
    salary: Optional[str]
    description_html: str
    description_text: Optional[str]  # Plain text version for search
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
class SAScrapingMetadata:
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
