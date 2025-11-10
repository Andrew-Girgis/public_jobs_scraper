"""
Parser utilities for Ontario job postings.

This module contains helper functions for parsing specific fields from Ontario job pages.
"""

import re
from datetime import datetime
from typing import Optional, Tuple


def parse_salary(salary_str: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Parse salary string to extract min, max, and period.
    
    Args:
        salary_str: Raw salary string (e.g., "$1,512.75  - $1,933.38 Per week*")
    
    Returns:
        Tuple of (salary_min, salary_max, salary_period)
    """
    if not salary_str:
        return None, None, None
    
    # Format: "$1,512.75  - $1,933.38 Per week*"
    salary_match = re.search(
        r'\$?([\d,]+\.?\d*)\s*-\s*\$?([\d,]+\.?\d*)\s*Per\s+(\w+)',
        salary_str,
        re.IGNORECASE
    )
    
    if salary_match:
        try:
            salary_min = float(salary_match.group(1).replace(',', ''))
            salary_max = float(salary_match.group(2).replace(',', ''))
            salary_period = salary_match.group(3).lower()
            return salary_min, salary_max, salary_period
        except ValueError:
            pass
    
    return None, None, None


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse Ontario date string to datetime object.
    
    Args:
        date_str: Date string (e.g., "Friday, November 21, 2025 11:59 pm EST")
    
    Returns:
        datetime object if parsing successful, None otherwise
    """
    if not date_str:
        return None
    
    # Try multiple date formats
    formats = [
        "%A, %B %d, %Y %I:%M %p %Z",  # Friday, November 21, 2025 11:59 pm EST
        "%A, %B %d, %Y %I:%M %p",      # Friday, November 21, 2025 11:59 pm
        "%A, %B %d, %Y",                # Friday, November 21, 2025
        "%B %d, %Y",                    # November 21, 2025
        "%Y-%m-%d",                     # 2025-11-21
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def extract_text_from_html(html: str) -> str:
    """
    Extract plain text from HTML string, removing all tags.
    
    Args:
        html: HTML string
    
    Returns:
        Plain text with HTML tags removed
    """
    return re.sub(r'<[^>]+>', '', html).strip()


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text (remove extra spaces, newlines).
    
    Args:
        text: Input text
    
    Returns:
        Text with normalized whitespace
    """
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
