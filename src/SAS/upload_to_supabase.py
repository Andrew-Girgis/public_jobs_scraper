"""
Upload Saskatchewan Jobs to Supabase

This script reads JSON files from data/SAS/jobs_json/ and uploads them
to the Supabase database using the sas_jobs table schema.
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
DATA_DIR = PROJECT_ROOT / "data" / "SAS" / "jobs_json"

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
    opportunity = job_posting.get("the_opportunity", {})
    responsibilities = job_posting.get("responsibilities_breakdown", {})
    qualifications = job_posting.get("qualifications", {})
    benefits = job_posting.get("benefits", {})
    additional = job_posting.get("additional", {})
    scraping_metadata = job_json.get("scraping_metadata", {})
    
    # Transform the data to match database schema
    db_data = {
        # Job Identification
        "job_id": scraping_metadata.get("job_id"),
        "job_title": metadata.get("job_title"),
        "competition_number": metadata.get("competition_number"),
        
        # Source Information
        "jurisdiction": source.get("jurisdiction", "Saskatchewan"),
        "job_board": source.get("job_board", "Government of Saskatchewan"),
        "url": source.get("url"),
        
        # Employment Details
        "employment_type": metadata.get("employment_type"),
        "location": metadata.get("location"),
        "ministry": metadata.get("ministry"),
        "grade": metadata.get("grade"),
        "hours_of_work": metadata.get("hours_of_work"),
        "number_of_openings": metadata.get("number_of_openings"),
        
        # Salary Information
        "salary_range": metadata.get("salary_range"),
        "salary_min": metadata.get("salary_min"),
        "salary_max": metadata.get("salary_max"),
        "salary_frequency": metadata.get("salary_frequency"),
        "salary_supplement": metadata.get("salary_supplement"),
        
        # Dates
        "closing_date": metadata.get("closing_date"),
        
        # Job Content
        "ministry_description": job_posting.get("ministry_description"),
        "full_description": job_posting.get("full_description"),
        
        # The Opportunity Section
        "opportunity_intro": opportunity.get("intro"),
        "opportunity_responsibilities": opportunity.get("responsibilities"),
        
        # Responsibilities Breakdown (5 categories)
        "strategic_leadership_planning": responsibilities.get("strategic_leadership_planning"),
        "technical_oversight": responsibilities.get("technical_oversight"),
        "information_knowledge_management": responsibilities.get("information_knowledge_management"),
        "stakeholder_engagement_collaboration": responsibilities.get("stakeholder_engagement_collaboration"),
        "team_resource_management": responsibilities.get("team_resource_management"),
        
        # Qualifications
        "ideal_candidate": qualifications.get("the_ideal_candidate"),
        "qualifications_intro": qualifications.get("intro"),
        "required_qualifications": qualifications.get("required_qualifications", []),
        "education_requirements": qualifications.get("education_requirements"),
        
        # Benefits
        "what_we_offer": benefits.get("what_we_offer"),
        "benefits_list": benefits.get("benefits_list", []),
        
        # Additional Information
        "diversity_statement": additional.get("diversity_statement"),
        "additional_notes": additional.get("additional_notes"),
        
        # Scraping Metadata
        "search_keyword": scraping_metadata.get("search_keyword"),
        "matched_keyword": scraping_metadata.get("matched_keyword"),
        "match_score": scraping_metadata.get("match_score"),
        "scraped_at": scraping_metadata.get("scraped_at"),
    }
    
    # Remove None values to let database defaults handle them
    return {k: v for k, v in db_data.items() if v is not None}


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
        response = client.table('sas_jobs').upsert(job_data, on_conflict='job_id').execute()
        
        job_id = job_data.get('job_id', 'unknown')
        title = job_data.get('job_title', 'Unknown')
        print(f"✓ Uploaded: {job_id} - {title}")
        return True
        
    except Exception as e:
        job_id = job_data.get('job_id', 'unknown')
        print(f"✗ Error uploading {job_id}: {e}")
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
    print("Saskatchewan Jobs Uploader")
    print("=" * 80)
    print(f"Data directory: {DATA_DIR}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Get all JSON files
    json_files = list(DATA_DIR.glob("sas_job_*.json"))
    total_files = len(json_files)
    
    if total_files == 0:
        print("No JSON files found in data/SAS/jobs_json/")
        return
    
    print(f"Found {total_files} job files")
    
    if limit:
        json_files = json_files[:limit]
        print(f"Limiting to first {limit} files")
    
    print()
    
    # Connect to Supabase (skip if dry run)
    if not dry_run:
        try:
            client = get_supabase_client()
            print("✓ Connected to Supabase")
            print()
        except ValueError as e:
            print(f"✗ {e}")
            return
    else:
        print("Dry run mode - skipping Supabase connection")
        print()
        client = None
    
    # Process each file
    successful = 0
    failed = 0
    
    for i, filepath in enumerate(json_files, 1):
        print(f"[{i}/{len(json_files)}] Processing {filepath.name}...", end=" ")
        
        # Load job data
        job_json = load_job_from_file(filepath)
        if not job_json:
            failed += 1
            continue
        
        # Transform to database format
        try:
            job_data = transform_job_data(job_json)
        except Exception as e:
            print(f"✗ Error transforming data: {e}")
            failed += 1
            continue
        
        if dry_run:
            # Just validate the file
            job_id = job_data.get('job_id', 'unknown')
            title = job_data.get('job_title', 'Unknown')
            ministry = job_data.get('ministry', 'unknown')
            print(f"✓ Valid: {job_id} - {title} ({ministry})")
            successful += 1
        else:
            # Upload to Supabase
            if upload_job(client, job_data):
                successful += 1
            else:
                failed += 1
    
    # Summary
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total files:  {len(json_files)}")
    print(f"Successful:   {successful}")
    print(f"Failed:       {failed}")
    print()
    
    if not dry_run and successful > 0:
        print(f"✓ {successful} jobs uploaded to Supabase!")
    elif dry_run:
        print(f"✓ All {successful} files are valid and ready to upload")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Upload Saskatchewan job postings to Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to validate files
  python src/SAS/upload_to_supabase.py --dry-run
  
  # Upload first 10 jobs (for testing)
  python src/SAS/upload_to_supabase.py --limit 10
  
  # Upload all jobs
  python src/SAS/upload_to_supabase.py
        """
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of jobs to upload (for testing)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files without uploading to Supabase"
    )
    
    args = parser.parse_args()
    
    upload_all_jobs(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
