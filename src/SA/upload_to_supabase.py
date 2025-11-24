"""
Upload South Australia Jobs to Supabase

This script reads JSON files from data/SA/jobs_json/ and uploads them
to the Supabase database using the sa_jobs table schema.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "SA" / "jobs_json"

# Load environment variables from .env file in project root
load_dotenv(PROJECT_ROOT / ".env")

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def get_supabase_client() -> Client:
    """
    Create and return a Supabase client.
    
    Returns:
        Supabase client instance
    
    Raises:
        ValueError: If credentials are not set
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY "
            "environment variables.\n\n"
            "Example:\n"
            "export SUPABASE_URL='https://your-project.supabase.co'\n"
            "export SUPABASE_KEY='your-service-role-key'\n"
        )
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def parse_sa_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parse SA date string to ISO format for database.
    
    Args:
        date_str: Date string (e.g., "14/11/2025", "28/11/2025 5:00 PM")
    
    Returns:
        ISO formatted date string or None
    """
    if not date_str or date_str == "Not specified":
        return None
    
    try:
        # Remove time portion if present (e.g., "28/11/2025 5:00 PM" -> "28/11/2025")
        date_part = date_str.split(' ')[0].strip()
        
        # Parse SA format: "DD/MM/YYYY"
        dt = datetime.strptime(date_part, "%d/%m/%Y")
        return dt.date().isoformat()
    except ValueError:
        try:
            # Try alternative formats
            for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
        except Exception:
            pass
    
    return None


def parse_salary(salary_str: Optional[str]) -> Dict[str, Any]:
    """
    Parse salary string to extract min and max.
    Note: SA salary formats are highly inconsistent. This is a basic parser.
    Consider using AI/LLM for better extraction.
    
    Args:
        salary_str: Salary string (e.g., "ASO7 - $108,109 - $116,864 per annum", "MAS3 $127,859 p.a.")
    
    Returns:
        Dictionary with salary_min, salary_max, salary_currency
    """
    result = {
        "salary_min": None,
        "salary_max": None,
        "salary_currency": "AUD"
    }
    
    if not salary_str:
        return result
    
    # Extract currency (default to AUD for SA)
    if "£" in salary_str:
        result["salary_currency"] = "GBP"
    elif "$" in salary_str:
        result["salary_currency"] = "AUD"
    elif "€" in salary_str:
        result["salary_currency"] = "EUR"
    
    # Extract salary amounts
    # Pattern: $30,000 or $30000 or 30,000 or 30000
    amounts = re.findall(r'[\£\$\€]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', salary_str)
    amounts = [float(a.replace(',', '')) for a in amounts]
    
    if len(amounts) >= 2:
        result["salary_min"] = min(amounts)
        result["salary_max"] = max(amounts)
    elif len(amounts) == 1:
        result["salary_min"] = amounts[0]
        result["salary_max"] = amounts[0]
    
    return result


def html_to_text(html_str: Optional[str]) -> Optional[str]:
    """
    Convert HTML to plain text for full-text search.
    
    Args:
        html_str: HTML content
    
    Returns:
        Plain text version
    """
    if not html_str:
        return None
    
    try:
        soup = BeautifulSoup(html_str, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    except Exception:
        return html_str


def transform_job_data(job_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the SA job JSON structure into a flat structure for the database.
    
    Args:
        job_json: Raw job data from JSON file
    
    Returns:
        Flattened dictionary ready for database insertion
    """
    # Parse salary (basic extraction - consider AI for better results)
    salary_info = parse_salary(job_json.get("salary"))
    
    # Parse dates
    posting_date_parsed = parse_sa_date(job_json.get("posting_date"))
    closing_date_parsed = parse_sa_date(job_json.get("closing_date"))
    
    # Get description_text (if not already in JSON, convert from HTML)
    description_text = job_json.get("description_text")
    if not description_text:
        description_text = html_to_text(job_json.get("description_html"))
    
    # Parse scraped_at timestamp
    scraped_at = job_json.get("scraped_at")
    if scraped_at and isinstance(scraped_at, str):
        try:
            scraped_at = datetime.fromisoformat(scraped_at).isoformat()
        except:
            scraped_at = None
    
    # Transform the data to match database schema
    db_data = {
        # Job Identification
        "job_id": job_json.get("job_id"),
        "reference_number": job_json.get("reference_number"),
        "job_title": job_json.get("job_title"),
        
        # Source Information
        "jurisdiction": "South Australia, Australia",
        "job_board": "I Work for SA",
        "agency": job_json.get("agency"),
        "url": job_json.get("job_url"),
        
        # Location
        "location": job_json.get("location"),
        
        # Employment Details
        "job_status": job_json.get("job_status"),
        "eligibility": job_json.get("eligibility"),
        
        # Dates
        "posting_date": job_json.get("posting_date"),
        "posting_date_parsed": posting_date_parsed,
        "closing_date": job_json.get("closing_date"),
        "closing_date_parsed": closing_date_parsed,
        
        # Salary Information
        "salary": job_json.get("salary"),
        "salary_min": salary_info["salary_min"],
        "salary_max": salary_info["salary_max"],
        "salary_currency": salary_info["salary_currency"],
        
        # Job Content
        "description_html": job_json.get("description_html"),
        "description_text": description_text,
        
        # Attachments (convert list to JSONB)
        "attachments": job_json.get("attachments", []),
        
        # Scraping Metadata
        "search_keyword": job_json.get("search_keyword"),
        "matched_keyword": job_json.get("matched_keyword"),
        "match_score": job_json.get("match_score"),
        "scraped_at": scraped_at,
        "scraper_version": job_json.get("scraper_version", "1.0"),
    }
    
    return db_data


def upload_job(supabase: Client, job_data: Dict[str, Any]) -> bool:
    """
    Upload a single job to Supabase.
    
    Args:
        supabase: Supabase client
        job_data: Job data dictionary
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use upsert to handle duplicates
        response = supabase.table("sa_jobs").upsert(
            job_data,
            on_conflict="job_id"
        ).execute()
        
        return True
    except Exception as e:
        print(f"  ❌ Error uploading job {job_data.get('job_id')}: {str(e)}")
        return False


def upload_all_jobs(dry_run: bool = False):
    """
    Upload all SA jobs from JSON files to Supabase.
    
    Args:
        dry_run: If True, only validate data without uploading
    """
    if not DATA_DIR.exists():
        print(f"❌ Data directory not found: {DATA_DIR}")
        return
    
    json_files = list(DATA_DIR.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {DATA_DIR}")
        return
    
    print(f"📊 Found {len(json_files)} SA job files")
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - No data will be uploaded")
        print()
    
    # Get Supabase client
    try:
        supabase = get_supabase_client()
        print("✅ Connected to Supabase")
        print()
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    successful = 0
    failed = 0
    
    for i, json_file in enumerate(json_files, 1):
        try:
            # Load JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                job_json = json.load(f)
            
            # Transform data
            job_data = transform_job_data(job_json)
            
            if dry_run:
                print(f"[{i}/{len(json_files)}] ✓ Validated: {job_data['job_title'][:50]}... (ID: {job_data['job_id']})")
                successful += 1
            else:
                # Upload to Supabase
                success = upload_job(supabase, job_data)
                
                if success:
                    print(f"[{i}/{len(json_files)}] ✅ Uploaded: {job_data['job_title'][:50]}... (ID: {job_data['job_id']})")
                    successful += 1
                else:
                    failed += 1
                    
        except Exception as e:
            print(f"[{i}/{len(json_files)}] ❌ Error processing {json_file.name}: {str(e)}")
            failed += 1
    
    # Print summary
    print()
    print("=" * 60)
    print("📊 Upload Summary")
    print("=" * 60)
    print(f"Total files: {len(json_files)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"Success rate: {(successful/len(json_files)*100):.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    # Check for dry run flag
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🔍 Running in DRY RUN mode")
        print()
    
    upload_all_jobs(dry_run=dry_run)
