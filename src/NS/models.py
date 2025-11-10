"""
Data models for Nova Scotia (NS) job postings.

This module defines the unified data structure for Nova Scotia government job postings.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class NSJob:
    """Represents a complete Nova Scotia job posting."""
    
    # Source
    jurisdiction: str = "Nova Scotia"
    job_board: str = "Government of Nova Scotia"
    source_url: Optional[str] = None
    
    # Identifiers
    job_id: str = None
    competition_number: Optional[str] = None
    
    # Metadata
    job_title: Optional[str] = None
    classification: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    type_of_employment: Optional[str] = None
    union_status: Optional[str] = None
    
    # Dates and Time
    closing_date: Optional[datetime] = None
    closing_time: Optional[str] = "11:59 PM"
    closing_timezone: str = "Atlantic Time"
    
    # Content Sections
    about_us_heading: Optional[str] = "About Us"
    about_us_body: Optional[str] = None
    
    about_opportunity_heading: Optional[str] = "About Our Opportunity"
    about_opportunity_body: Optional[str] = None
    
    primary_accountabilities_heading: Optional[str] = "Primary Accountabilities"
    primary_accountabilities_intro: Optional[str] = None
    primary_accountabilities_bullets: List[str] = field(default_factory=list)
    
    qualifications_heading: Optional[str] = "Qualifications and Experience"
    qualifications_requirements_intro: Optional[str] = None
    qualifications_required_education: Optional[str] = None
    qualifications_required_experience: Optional[str] = None
    qualifications_required_bullets: List[str] = field(default_factory=list)
    qualifications_additional_skills_bullets: List[str] = field(default_factory=list)
    qualifications_asset_heading: Optional[str] = "Assets"
    qualifications_asset_bullets: List[str] = field(default_factory=list)
    qualifications_equivalency_heading: Optional[str] = "Equivalency"
    qualifications_equivalency_text: Optional[str] = None
    
    benefits_heading: Optional[str] = "Benefits"
    benefits_body: Optional[str] = None
    benefits_link_text: Optional[str] = "Benefits for government employees"
    benefits_link_url: Optional[str] = None
    
    working_conditions_heading: Optional[str] = "Working Conditions"
    working_conditions_body: Optional[str] = None
    
    additional_information_heading: Optional[str] = "Additional Information"
    additional_information_body: Optional[str] = None
    
    what_we_offer_heading: Optional[str] = "What We Offer"
    what_we_offer_bullets: List[str] = field(default_factory=list)
    
    # Compensation
    pay_grade: Optional[str] = None
    salary_range_raw_text: Optional[str] = None
    salary_min_amount: Optional[float] = None
    salary_max_amount: Optional[float] = None
    salary_frequency: str = "Bi-Weekly"
    salary_currency: str = "CAD"
    
    # Statements
    employment_equity_heading: Optional[str] = "Employment Equity Statement"
    employment_equity_body: Optional[str] = None
    accommodation_heading: Optional[str] = "Accommodation Statement"
    accommodation_body: Optional[str] = None
    
    # Application Instructions
    internal_applicants_text: Optional[str] = None
    external_applicants_text: Optional[str] = None
    incomplete_applications_note: Optional[str] = None
    contact_email: str = "Competitions@novascotia.ca"
    
    # Metadata
    scraped_at: Optional[datetime] = None
    search_keyword: Optional[str] = None  # The keyword used in the search query
    matched_keyword: Optional[str] = None  # The keyword from list-of-jobs.txt that matched via token matching
    match_score: Optional[float] = None  # Match score
    
    def to_dict(self) -> dict:
        """
        Convert the job posting to a dictionary suitable for JSON serialization.
        
        Returns:
            Dictionary representation of the job posting
        """
        data = {
            "job_posting": {
                "source": {
                    "jurisdiction": self.jurisdiction,
                    "job_board": self.job_board,
                    "url": self.source_url
                },
                "metadata": {
                    "job_title": self.job_title,
                    "classification": self.classification,
                    "competition_number": self.competition_number,
                    "department": self.department,
                    "location": self.location,
                    "type_of_employment": self.type_of_employment,
                    "union_status": self.union_status,
                    "closing_date": self.closing_date.isoformat() if self.closing_date else None,
                    "closing_time": self.closing_time,
                    "closing_timezone": self.closing_timezone
                },
                "about_us": {
                    "heading": self.about_us_heading,
                    "body": self.about_us_body
                },
                "about_our_opportunity": {
                    "heading": self.about_opportunity_heading,
                    "body": self.about_opportunity_body
                },
                "primary_accountabilities": {
                    "heading": self.primary_accountabilities_heading,
                    "intro": self.primary_accountabilities_intro,
                    "bullets": self.primary_accountabilities_bullets
                },
                "qualifications_and_experience": {
                    "heading": self.qualifications_heading,
                    "requirements_intro": self.qualifications_requirements_intro,
                    "required_education": self.qualifications_required_education,
                    "required_experience": self.qualifications_required_experience,
                    "required_bullets": self.qualifications_required_bullets,
                    "additional_skills_bullets": self.qualifications_additional_skills_bullets,
                    "asset_heading": self.qualifications_asset_heading,
                    "asset_bullets": self.qualifications_asset_bullets,
                    "equivalency_heading": self.qualifications_equivalency_heading,
                    "equivalency_text": self.qualifications_equivalency_text
                },
                "benefits": {
                    "heading": self.benefits_heading,
                    "body": self.benefits_body,
                    "benefits_link_text": self.benefits_link_text,
                    "benefits_link_url": self.benefits_link_url
                },
                "working_conditions": {
                    "heading": self.working_conditions_heading,
                    "body": self.working_conditions_body
                },
                "additional_information": {
                    "heading": self.additional_information_heading,
                    "body": self.additional_information_body
                },
                "what_we_offer": {
                    "heading": self.what_we_offer_heading,
                    "bullets": self.what_we_offer_bullets
                },
                "compensation": {
                    "pay_grade": self.pay_grade,
                    "salary_range": {
                        "raw_text": self.salary_range_raw_text,
                        "min_amount": self.salary_min_amount,
                        "max_amount": self.salary_max_amount,
                        "frequency": self.salary_frequency,
                        "currency": self.salary_currency
                    }
                },
                "statements": {
                    "employment_equity": {
                        "heading": self.employment_equity_heading,
                        "body": self.employment_equity_body
                    },
                    "accommodation": {
                        "heading": self.accommodation_heading,
                        "body": self.accommodation_body
                    }
                },
                "application_instructions": {
                    "internal_applicants_text": self.internal_applicants_text,
                    "external_applicants_text": self.external_applicants_text,
                    "incomplete_applications_note": self.incomplete_applications_note,
                    "contact_email": self.contact_email
                }
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
