"""
Upload GOC Jobs to Supabase

This script reads JSON files from data/GOC/jobs_json/ and uploads them
to the Supabase database using the goc_jobs table schema.
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
DATA_DIR = PROJECT_ROOT / "data" / "GOC" / "jobs_json"

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


def upload_job(client: Client, job_data: Dict[str, Any]) -> bool:
    """
    Upload a single job to Supabase.
    
    Uses upsert to insert or update the job based on poster_id.
    
    Args:
        client: Supabase client instance
        job_data: Dictionary containing job information
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Upsert the job (insert or update if poster_id already exists)
        response = client.table('goc_jobs').upsert(job_data).execute()
        
        poster_id = job_data.get('poster_id', 'unknown')
        title = job_data.get('title', 'Unknown')
        print(f"✓ Uploaded: {poster_id} - {title}")
        return True
        
    except Exception as e:
        poster_id = job_data.get('poster_id', 'unknown')
        print(f"✗ Error uploading {poster_id}: {e}")
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
    print("GOC Jobs Uploader")
    print("=" * 80)
    print(f"Data directory: {DATA_DIR}")
    print(f"Dry run: {dry_run}")
    print()
    
    # Get all JSON files
    json_files = list(DATA_DIR.glob("*.json"))
    total_files = len(json_files)
    
    if total_files == 0:
        print("No JSON files found in data/GOC/jobs_json/")
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
        job_data = load_job_from_file(filepath)
        if not job_data:
            failed += 1
            continue
        
        if dry_run:
            # Just validate the file
            poster_id = job_data.get('poster_id', 'unknown')
            title = job_data.get('title', 'Unknown')
            structure = job_data.get('structure_type', 'unknown')
            print(f"✓ Valid: {poster_id} - {title} ({structure})")
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
        description="Upload GOC job postings to Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to validate files
  python src/GOC/upload_to_supabase.py --dry-run
  
  # Upload first 10 jobs (for testing)
  python src/GOC/upload_to_supabase.py --limit 10
  
  # Upload all jobs
  python src/GOC/upload_to_supabase.py
  
Environment Variables:
  SUPABASE_URL    Your Supabase project URL
  SUPABASE_KEY    Your Supabase service role key (or anon key for testing)
  
  You can set these in your shell:
    export SUPABASE_URL='https://xxxxx.supabase.co'
    export SUPABASE_KEY='your-key-here'
        """
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of jobs to upload'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate files without uploading to Supabase'
    )
    
    args = parser.parse_args()
    
    upload_all_jobs(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
