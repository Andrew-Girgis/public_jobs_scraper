"""
Upload British Columbia Jobs to Supabase

This script reads JSON files from data/BC/jobs_json/ and uploads them
to the Supabase database using the bc_jobs table schema.
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
DATA_DIR = PROJECT_ROOT / "data" / "BC" / "jobs_json"

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
        date_str: Date string (e.g., "11/17/2025" or "November 17, 2025")
    
    Returns:
        ISO formatted date string or None
    """
    if not date_str:
        return None
    
    try:
        # Parse common formats
        for fmt in ["%m/%d/%Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y"]:
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
    job_summary = job_posting.get("job_summary", {})
    about_org = job_summary.get("about_organization", {})
    about_unit = job_summary.get("about_business_unit", {})
    about_role = job_summary.get("about_role", {})
    position_req = job_posting.get("position_requirements", {})
    education_exp = position_req.get("education_and_experience", {})
    app_instr = job_posting.get("application_instructions", {})
    app_req = app_instr.get("requirements", {})
    hr_contact = app_instr.get("hr_contact", {})
    submission = app_instr.get("submission_method", {})
    tech_help = app_instr.get("technical_help_contact", {})
    working_bc = job_posting.get("working_for_bc_public_service", {})
    indigenous_service = working_bc.get("indigenous_applicant_advisory_service", {})
    attachments = job_posting.get("attachments", {})
    scraping_metadata = job_json.get("scraping_metadata", {})
    
    # Extract attachment files
    attachment_files = []
    for file_obj in attachments.get("job_description_files", []):
        if isinstance(file_obj, dict):
            attachment_files.append({
                "label": file_obj.get("label"),
                "path_or_url": file_obj.get("path_or_url")
            })
    
    # Transform the data to match database schema
    db_data = {
        # Job Identification
        "job_id": scraping_metadata.get("job_id") or metadata.get("posting_id"),
        "posting_id": metadata.get("posting_id"),
        "posting_title": metadata.get("posting_title"),
        "job_title": metadata.get("job_title"),
        
        # Source Information
        "jurisdiction": source.get("jurisdiction", "British Columbia"),
        "job_board": source.get("job_board", "BC Public Service"),
        "organization": source.get("organization"),
        "url": source.get("url"),
        
        # Classification Details
        "position_classification": metadata.get("position_classification"),
        "classification_code": metadata.get("classification_code"),
        "union": metadata.get("union"),
        "job_type": metadata.get("job_type"),
        "job_category": metadata.get("job_category"),
        
        # Work Arrangements
        "work_options": metadata.get("work_options"),
        "locations": metadata.get("locations", []),
        
        # Ministry/Organization Structure
        "ministry_organization": metadata.get("ministry_organization"),
        "ministry_branch_division": metadata.get("ministry_branch_division"),
        
        # Salary Information
        "salary_raw_text": salary.get("raw_text"),
        "salary_min": salary.get("min_amount"),
        "salary_max": salary.get("max_amount"),
        "salary_frequency": salary.get("frequency"),
        "salary_currency": salary.get("currency", "CAD"),
        "temporary_market_adjustment": salary.get("temporary_market_adjustment"),
        
        # Dates
        "close_date": parse_date(metadata.get("close_date")),
        "close_time": metadata.get("close_time", "11:00 pm Pacific Time"),
        "temporary_end_date": parse_date(metadata.get("temporary_end_date")),
        
        # Amendments
        "amendments": job_posting.get("amendments", []),
        
        # Job Summary Sections
        "about_organization_heading": about_org.get("heading"),
        "about_organization_body": about_org.get("body", []),
        "about_business_unit_heading": about_unit.get("heading"),
        "about_business_unit_body": about_unit.get("body", []),
        "about_role_heading": about_role.get("heading"),
        "about_role_body": about_role.get("body", []),
        "special_conditions": job_summary.get("special_conditions", []),
        "eligibility_list_note": job_summary.get("eligibility_list_note"),
        
        # Education and Experience Requirements
        "education_experience_paths": education_exp.get("required_paths", []),
        "equivalency_statement": education_exp.get("equivalency_statement"),
        "recent_experience_note": education_exp.get("recent_experience_note"),
        
        # Position Requirements
        "position_requirements_heading": position_req.get("heading", "Position requirements"),
        "required_experience_bullets": position_req.get("required_experience_bullets", []),
        "preferred_experience_bullets": position_req.get("preferred_experience_bullets", []),
        
        # Application Requirements
        "cover_letter_required": app_req.get("cover_letter_required", False),
        "resume_details_required": app_req.get("resume_details_required", True),
        "other_documents": app_req.get("other_documents", []),
        
        # Application Instructions
        "application_instructions_heading": app_instr.get("heading", "Application instructions"),
        "evaluation_note": app_instr.get("evaluation_note"),
        
        # HR Contact Information
        "hr_contact_name": hr_contact.get("name"),
        "hr_contact_title": hr_contact.get("title"),
        "hr_contact_email": hr_contact.get("email"),
        
        # Submission Details
        "submission_system_name": submission.get("system_name", "BC Public Service Recruitment System"),
        "submission_notes": submission.get("notes", []),
        "technical_help_email": tech_help.get("email", "BCPSA.Hiring.Centre@gov.bc.ca"),
        "technical_help_notes": tech_help.get("notes", []),
        "deadline_note": app_instr.get("deadline_note", "Applications will be accepted until 11:00pm Pacific Time on the closing date of the competition."),
        
        # Working for BC Public Service Section
        "diversity_statement": working_bc.get("diversity_statement"),
        "flexible_work_statement": working_bc.get("flexible_work_statement"),
        
        # Indigenous Applicant Advisory Service
        "indigenous_service_available": indigenous_service.get("available", True),
        "indigenous_service_description": indigenous_service.get("description"),
        "indigenous_service_email": indigenous_service.get("contact_email"),
        "indigenous_service_phone": indigenous_service.get("contact_phone"),
        
        # Employer Value Proposition
        "employer_value_proposition": working_bc.get("employer_value_proposition", []),
        
        # Attachments
        "attachment_files": attachment_files,
        
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
        response = client.table('bc_jobs').upsert(job_data, on_conflict='job_id').execute()
        
        job_id = job_data.get('job_id', 'unknown')
        title = job_data.get('posting_title', 'Unknown')
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
    print("British Columbia Jobs Uploader")
    print("=" * 80)
    print(f"Data directory: {DATA_DIR}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        print(f"✗ Data directory not found: {DATA_DIR}")
        return
    
    # Get all JSON files
    json_files = sorted(DATA_DIR.glob("bc_job_*.json"))
    
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
            import traceback
            traceback.print_exc()
            error_count += 1
            continue
        
        if dry_run:
            # Just show what would be uploaded
            job_id = job_data.get('job_id', 'unknown')
            title = job_data.get('posting_title', 'Unknown')
            print(f"  Would upload: {job_id} - {title}")
            print(f"    Required experience: {len(job_data.get('required_experience_bullets', []))} bullets")
            print(f"    Preferred experience: {len(job_data.get('preferred_experience_bullets', []))} bullets")
            print(f"    Attachments: {len(job_data.get('attachment_files', []))} files")
            print(f"    Work options: {job_data.get('work_options', 'N/A')}")
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
    
    parser = argparse.ArgumentParser(description="Upload BC jobs to Supabase")
    parser.add_argument("--limit", type=int, help="Limit number of jobs to upload")
    parser.add_argument("--dry-run", action="store_true", help="Validate files without uploading")
    
    args = parser.parse_args()
    
    upload_all_jobs(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
