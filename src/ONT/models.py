"""
Data models for Ontario (ONT) job postings.

This module defines the unified data structure for Ontario Public Service job postings.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class OntJob:
    """Represents a complete Ontario job posting."""
    
    # Identifiers
    job_id: str
    url: str
    
    # Basic Information
    title: str
    organization: Optional[str] = None
    division: Optional[str] = None
    city: Optional[str] = None
    
    # Job Details
    posting_status: Optional[str] = None
    position_language: Optional[str] = None
    job_term: Optional[str] = None
    job_code: Optional[str] = None
    salary: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_period: Optional[str] = None
    
    # Dates
    apply_by: Optional[datetime] = None
    posted_on: Optional[datetime] = None
    
    # Additional Details
    position_details: Optional[str] = None
    compensation_group: Optional[str] = None
    work_hours: Optional[str] = None
    category: Optional[str] = None
    note: Optional[str] = None
    
    # Content Sections
    about_the_job: Optional[str] = None
    what_you_bring: Optional[str] = None
    mandatory_requirements: Optional[str] = None
    additional_info: Optional[str] = None
    how_to_apply: Optional[str] = None
    
    # Metadata
    scraped_at: Optional[datetime] = None
    matched_keyword: Optional[str] = None  # The keyword from list-of-jobs.txt that matched
    match_score: Optional[float] = None  # Fuzzy match score
    
    def to_dict(self) -> dict:
        """
        Convert the job posting to a dictionary suitable for JSON serialization.
        
        Returns:
            Dictionary representation of the job posting
        """
        data = {}
        
        for key, value in self.__dict__.items():
            if value is None:
                data[key] = None
            elif isinstance(value, datetime):
                # Convert datetime to ISO format string
                data[key] = value.isoformat()
            else:
                data[key] = value
        
        return data


@dataclass
class JobMatch:
    """Represents a matched job from the search results."""
    
    job_id: str
    title: str
    url: str
    matched_keyword: str
    match_score: float
    page_number: int
