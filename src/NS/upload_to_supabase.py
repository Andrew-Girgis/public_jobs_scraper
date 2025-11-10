"""
Upload Nova Scotia jobs to Supabase database.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from NS.config import JOBS_JSON_DIR

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_supabase_client() -> Client:
    """Create and return Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def transform_job_for_db(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform JSON job data to database schema format.
    
    Args:
        job_data: Job data from JSON file
    
    Returns:
        Dictionary formatted for database insertion
    """
    jp = job_data.get("job_posting", {})
    source = jp.get("source", {})
    metadata = jp.get("metadata", {})
    about_us = jp.get("about_us", {})
    about_opp = jp.get("about_our_opportunity", {})
    primary_acc = jp.get("primary_accountabilities", {})
    qual = jp.get("qualifications_and_experience", {})
    benefits = jp.get("benefits", {})
    working = jp.get("working_conditions", {})
    additional = jp.get("additional_information", {})
    what_offer = jp.get("what_we_offer", {})
    compensation = jp.get("compensation", {})
    salary_range = compensation.get("salary_range", {})
    statements = jp.get("statements", {})
    equity = statements.get("employment_equity", {})
    accommodation = statements.get("accommodation", {})
    app_instr = jp.get("application_instructions", {})
    scraping_meta = job_data.get("scraping_metadata", {})
    
    # Parse closing date - convert to ISO string for Supabase
    closing_date = None
    if metadata.get("closing_date"):
        try:
            dt = datetime.fromisoformat(metadata["closing_date"].replace("Z", "+00:00"))
            closing_date = dt.isoformat()
        except (ValueError, AttributeError):
            pass
    
    # Parse scraped_at - convert to ISO string for Supabase
    scraped_at = None
    if scraping_meta.get("scraped_at"):
        try:
            dt = datetime.fromisoformat(scraping_meta["scraped_at"])
            scraped_at = dt.isoformat()
        except (ValueError, AttributeError):
            scraped_at = datetime.now().isoformat()
    
    return {
        # Primary key
        "job_id": scraping_meta.get("job_id"),
        
        # Source
        "jurisdiction": source.get("jurisdiction"),
        "job_board": source.get("job_board"),
        "url": source.get("url"),
        
        # Metadata
        "job_title": metadata.get("job_title"),
        "classification": metadata.get("classification"),
        "competition_number": metadata.get("competition_number"),
        "department": metadata.get("department"),
        "location": metadata.get("location"),
        "type_of_employment": metadata.get("type_of_employment"),
        "union_status": metadata.get("union_status"),
        "closing_date": closing_date,
        "closing_time": metadata.get("closing_time"),
        "closing_timezone": metadata.get("closing_timezone"),
        
        # Compensation
        "pay_grade": compensation.get("pay_grade"),
        "salary_range_raw": salary_range.get("raw_text"),
        "salary_min": salary_range.get("min_amount"),
        "salary_max": salary_range.get("max_amount"),
        "salary_frequency": salary_range.get("frequency"),
        "salary_currency": salary_range.get("currency", "CAD"),
        
        # Content sections
        "about_us_heading": about_us.get("heading"),
        "about_us_body": about_us.get("body"),
        
        "about_opportunity_heading": about_opp.get("heading"),
        "about_opportunity_body": about_opp.get("body"),
        
        "primary_accountabilities_heading": primary_acc.get("heading"),
        "primary_accountabilities_intro": primary_acc.get("intro"),
        "primary_accountabilities_bullets": primary_acc.get("bullets", []),
        
        "qualifications_heading": qual.get("heading"),
        "qualifications_requirements_intro": qual.get("requirements_intro"),
        "qualifications_required_education": qual.get("required_education"),
        "qualifications_required_experience": qual.get("required_experience"),
        "qualifications_required_bullets": qual.get("required_bullets", []),
        "qualifications_additional_skills_bullets": qual.get("additional_skills_bullets", []),
        "qualifications_asset_heading": qual.get("asset_heading"),
        "qualifications_asset_bullets": qual.get("asset_bullets", []),
        "qualifications_equivalency_heading": qual.get("equivalency_heading"),
        "qualifications_equivalency_text": qual.get("equivalency_text"),
        
        "benefits_heading": benefits.get("heading"),
        "benefits_body": benefits.get("body"),
        "benefits_link_text": benefits.get("benefits_link_text"),
        "benefits_link_url": benefits.get("benefits_link_url"),
        
        "working_conditions_heading": working.get("heading"),
        "working_conditions_body": working.get("body"),
        
        "additional_information_heading": additional.get("heading"),
        "additional_information_body": additional.get("body"),
        
        "what_we_offer_heading": what_offer.get("heading"),
        "what_we_offer_bullets": what_offer.get("bullets", []),
        
        # Statements
        "employment_equity_heading": equity.get("heading"),
        "employment_equity_body": equity.get("body"),
        
        "accommodation_heading": accommodation.get("heading"),
        "accommodation_body": accommodation.get("body"),
        
        # Application instructions
        "internal_applicants_text": app_instr.get("internal_applicants_text"),
        "external_applicants_text": app_instr.get("external_applicants_text"),
        "incomplete_applications_note": app_instr.get("incomplete_applications_note"),
        "contact_email": app_instr.get("contact_email"),
        
        # Scraping metadata
        "scraped_at": scraped_at,
        "search_keyword": scraping_meta.get("search_keyword"),
        "matched_keyword": scraping_meta.get("matched_keyword"),
        "match_score": scraping_meta.get("match_score"),
    }


def upload_job(client: Client, job_file: Path) -> bool:
    """
    Upload a single job to Supabase.
    
    Args:
        client: Supabase client
        job_file: Path to JSON file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load job data
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Transform to database format
        db_data = transform_job_for_db(job_data)
        
        # Upsert (insert or update if exists)
        result = client.table('ns_jobs').upsert(
            db_data,
            on_conflict='job_id'
        ).execute()
        
        print(f"✓ Uploaded job {db_data['job_id']}: {db_data['job_title']}")
        return True
        
    except Exception as e:
        print(f"✗ Error uploading {job_file.name}: {e}")
        return False


def upload_all_jobs(dry_run: bool = False) -> None:
    """
    Upload all NS jobs to Supabase.
    
    Args:
        dry_run: If True, only validate files without uploading
    """
    print("=" * 80)
    print("Nova Scotia Jobs Uploader")
    print("=" * 80)
    
    # Get all JSON files
    json_files = list(JOBS_JSON_DIR.glob("ns_job_*.json"))
    
    if not json_files:
        print("✗ No job files found in", JOBS_JSON_DIR)
        return
    
    print(f"Found {len(json_files)} job files")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No data will be uploaded")
        print("\nValidating files...")
        
        valid_count = 0
        for job_file in json_files:
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                db_data = transform_job_for_db(job_data)
                print(f"✓ {job_file.name}: {db_data['job_title']}")
                valid_count += 1
            except Exception as e:
                print(f"✗ {job_file.name}: {e}")
        
        print(f"\n✓ Validated {valid_count}/{len(json_files)} files")
        return
    
    # Upload to Supabase
    print("\n📤 Uploading to Supabase...")
    client = get_supabase_client()
    
    success_count = 0
    fail_count = 0
    
    for job_file in json_files:
        if upload_job(client, job_file):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("Upload Complete")
    print("=" * 80)
    print(f"✓ Successfully uploaded: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print(f"📊 Total: {len(json_files)}")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload NS jobs to Supabase")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files without uploading"
    )
    
    args = parser.parse_args()
    upload_all_jobs(dry_run=args.dry_run)
