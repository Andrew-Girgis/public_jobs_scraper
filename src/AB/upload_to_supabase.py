"""
Upload Alberta Jobs to Supabase

This script reads JSON files from data/AB/jobs_json/ and uploads them
to the Supabase database using the ab_jobs table schema.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "AB" / "jobs_json"

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
        date_str: Date string (e.g., "Nov 27, 2025" or "November 27, 2025")
    
    Returns:
        ISO formatted date string or None
    """
    if not date_str:
        return None
    
    try:
        # Parse common formats
        for fmt in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.date().isoformat()
            except ValueError:
                continue
        return None
    except Exception:
        return None


def extract_responsibility_groups(role_resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract responsibility groups with headings and items.
    
    Args:
        role_resp: Role responsibilities dictionary
    
    Returns:
        List of {heading, items} objects
    """
    groups = []
    for group in role_resp.get("responsibility_groups", []):
        if isinstance(group, dict):
            groups.append({
                "heading": group.get("heading"),
                "items": group.get("items", [])
            })
    return groups


def extract_resource_links(notes: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract benefit/resource links.
    
    Args:
        notes: Notes dictionary
    
    Returns:
        List of {label, url} objects
    """
    links = []
    for link in notes.get("benefits_and_resources_links", []):
        if isinstance(link, dict):
            links.append({
                "label": link.get("label"),
                "url": link.get("url")
            })
    return links


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
    header = job_posting.get("header", {})
    job_info = job_posting.get("job_information", {})
    salary = job_info.get("salary", {})
    diversity = job_posting.get("diversity_and_inclusion", {})
    ministry_overview = job_posting.get("ministry_overview", {})
    role_resp = job_posting.get("role_responsibilities", {})
    aps_comp = job_posting.get("aps_competencies", {})
    qualifications = job_posting.get("qualifications", {})
    required = qualifications.get("required", {})
    equivalency = qualifications.get("equivalency", {})
    assets = qualifications.get("assets", {})
    notes = job_posting.get("notes", {})
    how_to_apply = job_posting.get("how_to_apply", {})
    iqas = how_to_apply.get("iqas_recommendation", {})
    closing = job_posting.get("closing_statement", {})
    contact = closing.get("contact", {})
    scraping_metadata = job_json.get("scraping_metadata", {})
    
    # Transform the data to match database schema
    db_data = {
        # Job Identification
        "job_id": scraping_metadata.get("job_id"),
        "job_requisition_id": job_info.get("job_requisition_id"),
        "job_title": job_info.get("job_title") or header.get("job_title"),
        
        # Source Information
        "jurisdiction": source.get("jurisdiction", "Alberta"),
        "job_board": source.get("job_board", "Alberta Public Service Careers"),
        "company": source.get("company", "Government of Alberta"),
        "url": source.get("url"),
        
        # Classification and Job Details
        "classification": job_info.get("classification"),
        "ministry": job_info.get("ministry"),
        "location": job_info.get("location"),
        "location_line": header.get("location_line"),
        "full_or_part_time": job_info.get("full_or_part_time"),
        "hours_of_work": job_info.get("hours_of_work"),
        "permanent_or_temporary": job_info.get("permanent_or_temporary"),
        "scope": job_info.get("scope"),
        
        # Dates
        "posting_date": header.get("posting_date"),
        "closing_date": job_info.get("closing_date"),
        
        # Salary Information
        "salary_raw_text": salary.get("raw_text"),
        "salary_biweekly_min": salary.get("biweekly_min"),
        "salary_biweekly_max": salary.get("biweekly_max"),
        "salary_annual_min": salary.get("annual_min"),
        "salary_annual_max": salary.get("annual_max"),
        "salary_currency": salary.get("currency", "CAD"),
        "salary_primary_frequency": salary.get("primary_frequency"),
        
        # Ministry/Organization Overview
        "ministry_overview_heading": ministry_overview.get("heading"),
        "ministry_overview_body": ministry_overview.get("body", []),
        
        # Role Responsibilities
        "role_responsibilities_heading": role_resp.get("heading", "Role Responsibilities"),
        "role_responsibilities_tagline": role_resp.get("tagline"),
        "role_responsibilities_intro": role_resp.get("intro_paragraphs", []),
        "role_responsibilities_groups": extract_responsibility_groups(role_resp),
        "job_description_link_text": role_resp.get("job_description_link_text"),
        "job_description_url": role_resp.get("job_description_url"),
        
        # APS Competencies
        "aps_competencies_heading": aps_comp.get("heading", "APS Competencies"),
        "aps_competencies_description": aps_comp.get("description"),
        "aps_competencies_items": aps_comp.get("items", []),
        "aps_competencies_url": aps_comp.get("competencies_url", "https://www.alberta.ca/system/files/custom_downloaded_images/psc-alberta-public-service-competency-model.pdf"),
        
        # Qualifications
        "qualifications_heading": qualifications.get("heading", "Qualifications"),
        "required_education": required.get("education", []),
        "required_experience": required.get("experience", []),
        "required_other": required.get("other", []),
        "equivalency_text": equivalency.get("text"),
        "equivalency_rules": equivalency.get("rules", []),
        "asset_qualifications": assets.get("items", []),
        "minimum_recruitment_standards_url": qualifications.get("minimum_recruitment_standards_url", "https://www.alberta.ca/alberta-public-service-minimum-recruitment-standards"),
        
        # Notes Section
        "notes_heading": notes.get("heading", "Notes"),
        "notes_employment_term": notes.get("employment_term"),
        "notes_location_reminder": notes.get("location_reminder"),
        "notes_assessment_info": notes.get("assessment_info", []),
        "notes_security_screening": notes.get("security_screening", []),
        "notes_reuse_competition": notes.get("reuse_competition_note", []),
        "notes_costs": notes.get("costs_note", []),
        "notes_benefits_resources": extract_resource_links(notes),
        
        # How to Apply
        "how_to_apply_heading": how_to_apply.get("heading", "How To Apply"),
        "how_to_apply_instructions": how_to_apply.get("instructions", []),
        "job_application_resources_url": how_to_apply.get("job_application_resources_url", "https://www.alberta.ca/job-application-resources#before"),
        "recruitment_principles_url": how_to_apply.get("recruitment_principles_url", "https://www.alberta.ca/recruitment-principles"),
        "iqas_recommended": iqas.get("recommended", True),
        "iqas_url": iqas.get("iqas_url", "https://www.alberta.ca/international-qualifications-assessment.aspx"),
        "alliance_url": iqas.get("alliance_url", "https://canalliance.org/en/default.html"),
        
        # Closing Statement
        "closing_reuse_competition_note": closing.get("reuse_competition_note"),
        "closing_thanks_screening_note": closing.get("thanks_and_screening_note"),
        "closing_contact_name": contact.get("name"),
        "closing_contact_email": contact.get("email"),
        "closing_accommodation_note": closing.get("accommodation_note"),
        
        # Diversity and Inclusion
        "diversity_statement": diversity.get("statement"),
        "diversity_policy_url": diversity.get("policy_url", "https://www.alberta.ca/diversity-inclusion-policy.aspx"),
        
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
        response = client.table('ab_jobs').upsert(job_data, on_conflict='job_id').execute()
        
        job_id = job_data.get('job_id', 'unknown')
        title = job_data.get('job_title', 'Unknown')
        match_score = job_data.get('match_score', 'N/A')
        print(f"✓ Uploaded: {job_id} - {title} (match score: {match_score})")
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
    print("Alberta Jobs Uploader")
    print("=" * 80)
    print(f"Data directory: {DATA_DIR}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        print(f"✗ Data directory not found: {DATA_DIR}")
        return
    
    # Get all JSON files
    json_files = sorted(DATA_DIR.glob("ab_job_*.json"))
    
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
            title = job_data.get('job_title', 'Unknown')
            ministry = job_data.get('ministry', 'N/A')
            classification = job_data.get('classification', 'N/A')
            match_score = job_data.get('match_score', 'N/A')
            print(f"  Would upload: {job_id} - {title}")
            print(f"    Ministry: {ministry}")
            print(f"    Classification: {classification}")
            print(f"    Match score: {match_score}")
            print(f"    Required education: {len(job_data.get('required_education', []))} items")
            print(f"    Required experience: {len(job_data.get('required_experience', []))} items")
            print(f"    APS competencies: {len(job_data.get('aps_competencies_items', []))} items")
            print(f"    Salary: ${job_data.get('salary_annual_min', 0):,.0f} - ${job_data.get('salary_annual_max', 0):,.0f}")
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
    
    parser = argparse.ArgumentParser(description="Upload Alberta jobs to Supabase")
    parser.add_argument("--limit", type=int, help="Limit number of jobs to upload")
    parser.add_argument("--dry-run", action="store_true", help="Validate files without uploading")
    
    args = parser.parse_args()
    
    upload_all_jobs(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
