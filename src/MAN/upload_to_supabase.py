"""
Upload Manitoba Jobs to Supabase

This script reads JSON files from data/MAN/jobs_json/ and uploads them
to the Supabase database using the man_jobs table schema.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "MAN" / "jobs_json"

# Load environment variables from .env file in project root
load_dotenv(PROJECT_ROOT / ".env")

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Check for SUPABASE_KEY first, then fall back to SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY
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


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """
    Parse date string to ISO format for database.
    
    Args:
        date_str: Date string (e.g., "November 16, 2025")
    
    Returns:
        ISO formatted date string or None
    """
    if not date_str:
        return None
    
    try:
        # Parse common formats
        for fmt in ["%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.date().isoformat()
            except ValueError:
                continue
        return None
    except Exception:
        return None


def transform_job_data(job_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the nested JSON structure into a flat structure for the database.
    
    Args:
        job_json: Raw job data from JSON file
    
    Returns:
        Flattened dictionary ready for database insertion
    """
    job_posting = job_json.get("job_posting", {})
    source = job_posting.get("source", {})
    metadata = job_posting.get("metadata", {})
    salary = metadata.get("salary", {})
    employment_equity = job_posting.get("employment_equity", {})
    competition_notes = job_posting.get("competition_notes", {})
    position_overview = job_posting.get("position_overview", {})
    benefits = job_posting.get("benefits", {})
    conditions = job_posting.get("conditions_of_employment", {})
    qualifications = job_posting.get("qualifications", {})
    duties = job_posting.get("duties", {})
    application = job_posting.get("application_instructions", {})
    apply_to = application.get("apply_to_block", {})
    scraping_metadata = job_json.get("scraping_metadata", {})
    
    # Transform the data to match database schema
    db_data = {
        # Job Identification
        "job_id": scraping_metadata.get("job_id"),
        "job_title": metadata.get("job_title"),
        "advertisement_number": metadata.get("advertisement_number"),
        
        # Source Information
        "jurisdiction": source.get("jurisdiction", "Manitoba"),
        "job_board": source.get("job_board", "Government of Manitoba Careers"),
        "url": source.get("url"),
        
        # Employment Details
        "classification_title": metadata.get("classification_title"),
        "classification_code": metadata.get("classification_code"),
        "employment_types": metadata.get("employment_types", []),
        "departments": metadata.get("departments", []),
        "divisions": metadata.get("divisions", []),
        "locations": metadata.get("locations", []),
        
        # Salary Information
        "salary_raw_text": salary.get("raw_text"),
        "salary_classification_code": salary.get("classification_code"),
        "salary_min": salary.get("min_amount"),
        "salary_max": salary.get("max_amount"),
        "salary_frequency": salary.get("frequency"),
        "salary_currency": salary.get("currency", "CAD"),
        
        # Dates
        "closing_date": parse_date(metadata.get("closing_date")),
        "closing_time": metadata.get("closing_time"),
        
        # Employment Equity
        "employment_equity_intro": employment_equity.get("intro_paragraph"),
        "employment_equity_statement": employment_equity.get("equity_factor_statement"),
        "designated_groups": employment_equity.get("designated_groups", []),
        
        # Competition Notes
        "eligibility_list_text": competition_notes.get("eligibility_list_text"),
        "classification_flex_text": competition_notes.get("classification_flex_text"),
        "competition_usage_text": competition_notes.get("usage_text"),
        
        # Position Overview
        "position_summary_paragraphs": position_overview.get("summary_paragraphs", []),
        
        # Benefits
        "benefits_summary": benefits.get("summary_paragraph"),
        "benefits_items": benefits.get("benefit_items", []),
        
        # Conditions of Employment
        "conditions_heading": conditions.get("heading"),
        "conditions_items": conditions.get("items", []),
        
        # Qualifications
        "qualifications_heading": qualifications.get("heading"),
        "essential_qualifications": qualifications.get("essential", []),
        "desired_qualifications": qualifications.get("desired", []),
        "qualifications_equivalency_text": qualifications.get("equivalency_text"),
        
        # Duties
        "duties_heading": duties.get("heading"),
        "duties_intro": duties.get("intro"),
        "duties_items": duties.get("items", []),
        
        # Application Instructions
        "application_form_required": application.get("requires_application_form", False),
        "application_form_link_text": application.get("application_form_link_text"),
        "application_form_url": application.get("application_form_url"),
        "application_instructions": application.get("instruction_text", []),
        "accommodation_text": application.get("accommodation_text"),
        "grievance_notice": application.get("grievance_notice"),
        "contact_note": application.get("contact_note"),
        
        # Apply To Block
        "apply_to_unit": apply_to.get("unit"),
        "apply_to_branch": apply_to.get("branch"),
        "apply_to_address": apply_to.get("address_lines", []),
        "apply_to_phone": apply_to.get("phone"),
        "apply_to_fax": apply_to.get("fax"),
        "apply_to_email": apply_to.get("email"),
        
        # Scraping Metadata
        "search_keyword": job_posting.get("search_keyword"),
        "matched_keyword": scraping_metadata.get("matched_keyword"),
        "match_score": scraping_metadata.get("match_score"),
        "scraped_at": scraping_metadata.get("scraped_at"),
    }
    
    # Remove None values to let database defaults handle them
    # But keep empty lists for JSONB columns
    return {k: v for k, v in db_data.items() if v is not None or isinstance(v, list)}


def upload_job(client: Client, job_data: Dict[str, Any]) -> bool:
    """
    Upload a single job to Supabase.
    
    Uses upsert to insert or update the job based on job_id.
    
    Args:
        client: Supabase client instance
        job_data: Dictionary containing job information
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Upsert the job (insert or update if job_id already exists)
        response = client.table('man_jobs').upsert(job_data, on_conflict='job_id').execute()
        
        job_id = job_data.get('job_id', 'unknown')
        title = job_data.get('job_title', 'Unknown')
        print(f"✓ Uploaded: {job_id} - {title}")
        return True
        
    except Exception as e:
        job_id = job_data.get('job_id', 'unknown')
        print(f"✗ Error uploading {job_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_job_from_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Load job data from a JSON file.
    
    Args:
        filepath: Path to the JSON file
    
    Returns:
        Dictionary containing job data, or None if loading fails
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"✗ Error loading {filepath.name}: {e}")
        return None


def upload_all_jobs(limit: Optional[int] = None, dry_run: bool = False):
    """
    Upload all jobs from the jobs_json directory to Supabase.
    
    Args:
        limit: Maximum number of jobs to upload (None for all)
        dry_run: If True, only validate files without uploading
    """
    print("=" * 80)
    print("Manitoba Jobs Uploader")
    print("=" * 80)
    print(f"Data directory: {DATA_DIR}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        print(f"✗ Data directory not found: {DATA_DIR}")
        return
    
    # Get all JSON files
    json_files = sorted(DATA_DIR.glob("man_job_*.json"))
    
    if not json_files:
        print(f"✗ No job files found in {DATA_DIR}")
        return
    
    print(f"Found {len(json_files)} job file(s)")
    
    if limit:
        json_files = json_files[:limit]
        print(f"Processing first {limit} file(s)")
    
    print()
    
    # Create Supabase client (skip if dry run)
    if not dry_run:
        try:
            client = get_supabase_client()
            print("✓ Connected to Supabase")
            print()
        except ValueError as e:
            print(f"✗ {e}")
            return
    else:
        print("Dry run mode - skipping upload")
        print()
    
    # Process each file
    success_count = 0
    error_count = 0
    
    for i, filepath in enumerate(json_files, 1):
        print(f"[{i}/{len(json_files)}] Processing {filepath.name}...")
        
        # Load job data
        job_json = load_job_from_file(filepath)
        if not job_json:
            error_count += 1
            continue
        
        # Transform data
        try:
            job_data = transform_job_data(job_json)
        except Exception as e:
            print(f"✗ Error transforming {filepath.name}: {e}")
            error_count += 1
            continue
        
        if dry_run:
            # Just show what would be uploaded
            job_id = job_data.get('job_id', 'unknown')
            title = job_data.get('job_title', 'Unknown')
            print(f"  Would upload: {job_id} - {title}")
            print(f"    Essential quals: {len(job_data.get('essential_qualifications', []))}")
            print(f"    Desired quals: {len(job_data.get('desired_qualifications', []))}")
            print(f"    Duties: {len(job_data.get('duties_items', []))}")
            success_count += 1
        else:
            # Upload to Supabase
            if upload_job(client, job_data):
                success_count += 1
            else:
                error_count += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("Upload Summary")
    print("=" * 80)
    print(f"Total files: {len(json_files)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print()


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload Manitoba jobs to Supabase")
    parser.add_argument("--limit", type=int, help="Limit number of jobs to upload")
    parser.add_argument("--dry-run", action="store_true", help="Validate files without uploading")
    
    args = parser.parse_args()
    
    upload_all_jobs(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
