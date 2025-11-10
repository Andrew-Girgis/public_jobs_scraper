"""
Data models for Saskatchewan (SAS) job postings.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class SASJob:
    """
    Represents a Saskatchewan government job posting from govskpsc.taleo.net.
    """
    
    # Primary identifier
    job_id: Optional[str] = None
    
    # Source information
    jurisdiction: str = "Saskatchewan"
    job_board: str = "Government of Saskatchewan"
    url: Optional[str] = None
    
    # Job metadata
    job_title: Optional[str] = None
    employment_type: Optional[str] = None  # e.g., "Permanent Full-time"
    location: Optional[str] = None  # e.g., "SK-Rgna-Regina"
    ministry: Optional[str] = None  # e.g., "032 Health"
    salary_range: Optional[str] = None  # e.g., "$9,515-$12,367 Monthly"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_frequency: Optional[str] = None  # Monthly, Annual, etc.
    grade: Optional[str] = None  # e.g., "MCP.09."
    hours_of_work: Optional[str] = None  # e.g., "M - Monthly Out of Scope"
    number_of_openings: Optional[int] = None
    closing_date: Optional[datetime] = None
    
    # Content sections
    ministry_description: Optional[str] = None  # First paragraph about the ministry
    the_opportunity: Optional[str] = None  # The Opportunity section
    responsibilities: Optional[str] = None  # Reporting to... responsibilities
    
    # Responsibilities breakdown (if structured)
    strategic_leadership_planning: Optional[str] = None
    technical_oversight: Optional[str] = None
    information_knowledge_management: Optional[str] = None
    stakeholder_engagement_collaboration: Optional[str] = None
    team_resource_management: Optional[str] = None
    
    # Qualifications
    the_ideal_candidate: Optional[str] = None  # The Ideal Candidate section
    qualifications_intro: Optional[str] = None  # "You are a results-oriented leader..."
    required_qualifications: List[str] = field(default_factory=list)  # Bullet points
    education_requirements: Optional[str] = None  # "Typically, the knowledge..."
    
    # Benefits
    what_we_offer: Optional[str] = None  # What We Offer section
    benefits_list: List[str] = field(default_factory=list)  # Bullet points of benefits
    
    # Additional
    diversity_statement: Optional[str] = None  # "We are committed to workplace diversity"
    additional_notes: Optional[str] = None  # Any other information
    
    # Full content (raw)
    full_description: Optional[str] = None  # Complete job description
    
    # Scraping metadata
    scraped_at: Optional[datetime] = None
    search_keyword: Optional[str] = None  # The keyword used in the search query
    matched_keyword: Optional[str] = None  # The keyword from list-of-jobs.txt that matched
    match_score: Optional[float] = None  # Match score from token matching
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the job posting to a dictionary format suitable for JSON export.
        
        Returns:
            Dictionary representation of the job posting
        """
        data = {
            "job_posting": {
                "source": {
                    "jurisdiction": self.jurisdiction,
                    "job_board": self.job_board,
                    "url": self.url
                },
                "metadata": {
                    "job_title": self.job_title,
                    "employment_type": self.employment_type,
                    "location": self.location,
                    "ministry": self.ministry,
                    "salary_range": self.salary_range,
                    "salary_min": self.salary_min,
                    "salary_max": self.salary_max,
                    "salary_frequency": self.salary_frequency,
                    "grade": self.grade,
                    "hours_of_work": self.hours_of_work,
                    "number_of_openings": self.number_of_openings,
                    "closing_date": self.closing_date.isoformat() if self.closing_date else None
                },
                "ministry_description": self.ministry_description,
                "the_opportunity": {
                    "intro": self.the_opportunity,
                    "responsibilities": self.responsibilities
                },
                "responsibilities_breakdown": {
                    "strategic_leadership_planning": self.strategic_leadership_planning,
                    "technical_oversight": self.technical_oversight,
                    "information_knowledge_management": self.information_knowledge_management,
                    "stakeholder_engagement_collaboration": self.stakeholder_engagement_collaboration,
                    "team_resource_management": self.team_resource_management
                },
                "qualifications": {
                    "the_ideal_candidate": self.the_ideal_candidate,
                    "intro": self.qualifications_intro,
                    "required_qualifications": self.required_qualifications,
                    "education_requirements": self.education_requirements
                },
                "benefits": {
                    "what_we_offer": self.what_we_offer,
                    "benefits_list": self.benefits_list
                },
                "additional": {
                    "diversity_statement": self.diversity_statement,
                    "additional_notes": self.additional_notes
                },
                "full_description": self.full_description
            },
            "scraping_metadata": {
                "job_id": self.job_id,
                "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
                "search_keyword": self.search_keyword,
                "matched_keyword": self.matched_keyword,
                "match_score": self.match_score
            }
        }
        
        return data
