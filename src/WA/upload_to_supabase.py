"""
Upload Western Australia Jobs to Supabase

This script reads JSON files from data/WA/jobs_json/ and uploads them
to the Supabase database using the wa_jobs table schema.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "WA" / "jobs_json"

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


def parse_wa_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parse WA date string to ISO format for database.
    
    Args:
        date_str: Date string (e.g., "2025-12-08 4:00 PM", "2025-11-25 4:30 PM")
    
    Returns:
        ISO formatted datetime string with timezone or None
    """
    if not date_str or date_str == "Not specified":
        return None
    
    try:
        # WA format: "2025-12-08 4:00 PM"
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %I:%M %p")
        # Add AWST timezone (UTC+8)
        return dt.isoformat()
    except ValueError:
        try:
            # Try alternative formats
            for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %I:%M %p", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
        except Exception:
            pass
    
    return None


def parse_salary(salary_str: Optional[str]) -> Dict[str, Any]:
    """
    Parse salary string to extract min and max.
    
    Args:
        salary_str: Salary string (e.g., "$120,475-$132,753", "Teacher, $85,610 - $124,016 per annum (pro-rata)")
    
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
    
    # Extract currency (default to AUD for WA)
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


def transform_attachments(attachments: Optional[List[Dict[str, str]]]) -> Optional[Dict]:
    """
    Transform attachments list to JSONB format.
    
    Args:
        attachments: List of attachment dicts with 'name' and 'url' keys
    
    Returns:
        JSONB-compatible dict or None
    """
    if not attachments or not isinstance(attachments, list):
        return None
    
    # Return as-is for JSONB storage
    return attachments if len(attachments) > 0 else None


def transform_job_data(job_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the WA job JSON structure into a flat structure for the database.
    
    Args:
        job_json: Raw job data from JSON file
    
    Returns:
        Flattened dictionary ready for database insertion
    """
    # Parse salary
    salary_info = parse_salary(job_json.get("salary"))
    
    # Parse dates
    closing_date_parsed = parse_wa_date(job_json.get("closing_date"))
    
    # Parse scraped_at timestamp
    scraped_at = job_json.get("scraped_at")
    if scraped_at and isinstance(scraped_at, str):
        try:
            scraped_at = datetime.fromisoformat(scraped_at).isoformat()
        except:
            scraped_at = None
    
    # Transform attachments to JSONB
    attachments_jsonb = transform_attachments(job_json.get("attachments"))
    
    # Transform the data to match database schema
    db_data = {
        # Job Identification
        "job_id": job_json.get("job_id"),
        "position_number": job_json.get("position_number"),
        "job_title": job_json.get("job_title"),
        
        # Source Information
        "jurisdiction": "Western Australia, Australia",
        "job_board": "Jobs.WA",
        "agency": job_json.get("agency"),
        "branch": job_json.get("branch"),
        "division_name": job_json.get("division_name"),
        "url": job_json.get("job_url"),
        
        # Location
        "location": job_json.get("location"),
        
        # Employment Details
        "job_type": job_json.get("job_type"),
        "classification": job_json.get("classification"),
        
        # Dates
        "posting_date": job_json.get("posting_date"),
        "closing_date": job_json.get("closing_date"),
        "closing_date_parsed": closing_date_parsed,
        
        # Salary Information
        "salary": job_json.get("salary"),
        "salary_min": salary_info["salary_min"],
        "salary_max": salary_info["salary_max"],
        "salary_currency": salary_info["salary_currency"],
        
        # Job Content
        "description_html": job_json.get("description_html"),
        "description_text": job_json.get("description_text"),
        
        # Attachments (JSONB)
        "attachments": attachments_jsonb,
        
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
        response = supabase.table("wa_jobs").upsert(
            job_data,
            on_conflict="job_id"
        ).execute()
        
        return True
    except Exception as e:
        print(f"  ❌ Error uploading job {job_data.get('job_id')}: {str(e)}")
        return False


def upload_all_jobs(dry_run: bool = False):
    """
    Upload all WA jobs from JSON files to Supabase.
    
    Args:
        dry_run: If True, don't actually upload to Supabase
    """
    print("=" * 80)
    print("WA JOBS UPLOAD TO SUPABASE")
    print("=" * 80)
    print()
    
    # Get Supabase client
    if not dry_run:
        try:
            supabase = get_supabase_client()
            print(f"✅ Connected to Supabase: {SUPABASE_URL}")
        except ValueError as e:
            print(f"❌ {str(e)}")
            return
    else:
        print("🔍 DRY RUN MODE - No data will be uploaded")
        supabase = None
    
    print()
    
    # Get all JSON files
    if not DATA_DIR.exists():
        print(f"❌ Data directory not found: {DATA_DIR}")
        return
    
    json_files = sorted(DATA_DIR.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {DATA_DIR}")
        return
    
    print(f"📁 Found {len(json_files)} job files to process")
    print()
    
    # Stats
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # Process each file
    for json_file in json_files:
        stats["total"] += 1
        job_id = json_file.stem
        
        try:
            # Read JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                job_json = json.load(f)
            
            # Validate required fields
            if not job_json.get("job_id"):
                print(f"⏭️  [{stats['total']}/{len(json_files)}] Skipping {job_id}: Missing job_id")
                stats["skipped"] += 1
                continue
            
            if not job_json.get("description_html") or not job_json.get("description_text"):
                print(f"⏭️  [{stats['total']}/{len(json_files)}] Skipping {job_id}: Missing description")
                stats["skipped"] += 1
                continue
            
            # Transform data
            db_data = transform_job_data(job_json)
            
            # Upload to Supabase
            if dry_run:
                print(f"🔍 [{stats['total']}/{len(json_files)}] Would upload: {job_id} - {db_data['job_title'][:60]}")
                stats["success"] += 1
            else:
                success = upload_job(supabase, db_data)
                
                if success:
                    print(f"✅ [{stats['total']}/{len(json_files)}] Uploaded: {job_id} - {db_data['job_title'][:60]}")
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
        
        except Exception as e:
            print(f"❌ [{stats['total']}/{len(json_files)}] Error processing {job_id}: {str(e)}")
            stats["failed"] += 1
    
    # Print summary
    print()
    print("=" * 80)
    print("UPLOAD SUMMARY")
    print("=" * 80)
    print(f"Total files: {stats['total']}")
    print(f"✅ Successfully uploaded: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"⏭️  Skipped: {stats['skipped']}")
    print()
    
    if dry_run:
        print("🔍 This was a DRY RUN. Run without --dry-run to actually upload.")
    elif stats['success'] > 0:
        print(f"🎉 Upload complete! {stats['success']} jobs uploaded to Supabase.")


if __name__ == "__main__":
    import sys
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    
    upload_all_jobs(dry_run=dry_run)
