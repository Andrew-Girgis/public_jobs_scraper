"""
AI-based HTML extraction for WA Government Jobs

This script uses OpenAI API to extract structured data from WA job HTML files.
The WA job board has inconsistent HTML structures, making traditional parsing fragile.
AI extraction handles variability better and can extract complex nested information.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import openai
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HTML_DIR = PROJECT_ROOT / "data" / "WA" / "job_html"
JSON_DIR = PROJECT_ROOT / "data" / "WA" / "jobs_json"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

# Get OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

openai.api_key = OPENAI_API_KEY


def extract_job_content_table(html: str) -> str:
    """
    Extract only the relevant job content table from HTML.
    This focuses the AI on the actual job details, reducing token count.
    Handles multiple WA job board template formats.
    
    Args:
        html: Raw HTML content
    
    Returns:
        Extracted job content HTML (focused on job details)
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Strategy 1: Look for div with class 'advert-data' (common format)
    advert_data = soup.find('div', class_='advert-data')
    if advert_data:
        for script in advert_data(["script", "style"]):
            script.decompose()
        return str(advert_data)
    
    # Strategy 2: Look for tables with job content (GESB, Education templates)
    # Find table containing bodyText divs with substantial content
    tables_with_content = soup.find_all('table', role='presentation')
    for table in tables_with_content:
        body_text_divs = table.find_all('div', class_='bodyText')
        # Check if this table has substantial text content
        total_text = ''.join(div.get_text(strip=True) for div in body_text_divs)
        if len(total_text) > 500:  # Has meaningful content
            for script in table(["script", "style"]):
                script.decompose()
            return str(table)
    
    # Strategy 3: Look for summaryBox and bodyText sections (Education Dept format)
    summary_box = soup.find('div', id='summaryBox')
    if summary_box:
        # Find parent table that contains both summary and content
        parent_table = summary_box.find_parent('table')
        if parent_table:
            for script in parent_table(["script", "style"]):
                script.decompose()
            return str(parent_table)
    
    # Strategy 4: Look for contentCell (GESB format)
    content_cell = soup.find('td', id='contentCell')
    if content_cell:
        for script in content_cell(["script", "style"]):
            script.decompose()
        return str(content_cell)
    
    # Strategy 5: Find the form with job content
    form = soup.find('form', {'name': 'frmapply'})
    if form:
        for script in form(["script", "style"]):
            script.decompose()
        return str(form)
    
    # Last resort: clean the whole HTML and return
    for script in soup(["script", "style"]):
        script.decompose()
    return str(soup)


def extract_job_data_with_ai(html: str, job_id: str) -> Optional[Dict[str, Any]]:
    """
    Use OpenAI to extract structured job data from HTML.
    
    Args:
        html: HTML content of job page
        job_id: Job ID for context
    
    Returns:
        Dictionary with extracted job data, or None if extraction fails
    """
    # Extract only the job content table
    job_content = extract_job_content_table(html)
    
    # Truncate if too long (OpenAI has token limits)
    if len(job_content) > 20000:
        job_content = job_content[:20000] + "... [truncated]"
    
    prompt = f"""Extract structured job information from this WA Government job posting HTML.

HTML Content:
{job_content}

Extract the following fields and return ONLY a valid JSON object (no markdown, no code blocks, just the JSON):

{{
  "position_number": "string - the position/reference number (e.g., IR030362, 37521)",
  "job_title": "string - the job title",
  "agency": "string - the government agency/department",
  "branch": "string or null - the branch/division if mentioned",
  "location": "string - the job location/city",
  "classification": "string - job classification/level (e.g., Level 6, ASO7)",
  "salary": "string - full salary information including range and any benefits",
  "job_type": "string - employment type (e.g., Permanent - Full Time, Contract)",
  "closing_date": "string - application closing date with time (e.g., 2025-12-03 4:00 PM)",
  "division_name": "string or null - division name if different from branch",
  "description_html": "string - the full job description as HTML (all paragraphs and formatting)",
  "description_text": "string - plain text version of the description (no HTML tags)",
  "attachments": [
    {{"name": "string - attachment filename", "url": "string - full URL to attachment"}}
  ]
}}

Rules:
1. Return ONLY the JSON object, no other text
2. Use null for any field that isn't found or isn't applicable
3. Preserve HTML formatting in description_html
4. Extract ALL paragraphs for description, not just a summary
5. For description_text, convert description_html to plain text (remove all HTML tags)
6. Make attachment URLs absolute (prepend https://search.jobs.wa.gov.au if they start with /)
7. Clean up any label prefixes (e.g., "Position number :" should be removed, just return the number)
"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cost-effective
            messages=[
                {"role": "system", "content": "You are a data extraction assistant that extracts structured information from HTML. You always return valid JSON only, with no markdown formatting or code blocks."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},  # Force valid JSON output
            temperature=0,  # Deterministic output
            max_tokens=16000  # Increased to handle large job descriptions
        )

        # Get the response content
        content = response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # Parse JSON
        job_data = json.loads(content)
        return job_data

    except json.JSONDecodeError as e:
        print(f"  ❌ Failed to parse AI response as JSON for job {job_id}: {str(e)}")
        print(f"  Response was: {content[:200]}...")
        # Save raw response for debugging
        debug_dir = PROJECT_ROOT / "data" / "WA" / "ai_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_file = debug_dir / f"{job_id}_ai_response.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Raw AI response saved to {debug_file}")
        return None
    except Exception as e:
        print(f"  ❌ AI extraction failed for job {job_id}: {str(e)}")
        return None


def process_html_file(html_file: Path, existing_json: Dict[str, Any]) -> bool:
    """
    Process a single HTML file and update the JSON with AI-extracted data.
    
    Args:
        html_file: Path to HTML file
        existing_json: Existing JSON data from scraper
    
    Returns:
        True if successful, False otherwise
    """
    job_id = html_file.stem
    
    print(f"🤖 Processing job {job_id}...")
    
    # Read HTML file
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        print(f"  ❌ Failed to read HTML file: {str(e)}")
        return False
    
    # Extract data with AI
    extracted_data = extract_job_data_with_ai(html, job_id)
    
    if not extracted_data:
        return False
    
    # Merge with existing data (keep scraping metadata)
    updated_json = {
        **existing_json,  # Keep original metadata
        "position_number": extracted_data.get("position_number"),
        "agency": extracted_data.get("agency"),
        "branch": extracted_data.get("branch"),
        "location": extracted_data.get("location"),
        "classification": extracted_data.get("classification"),
        "salary": extracted_data.get("salary"),
        "job_type": extracted_data.get("job_type"),
        "closing_date": extracted_data.get("closing_date"),
        "division_name": extracted_data.get("division_name"),
        "description_html": extracted_data.get("description_html", ""),
        "description_text": extracted_data.get("description_text"),
        "attachments": extracted_data.get("attachments", []),
    }
    
    # Save updated JSON
    json_file = JSON_DIR / f"{job_id}.json"
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(updated_json, f, indent=2, ensure_ascii=False)
        print(f"  ✅ Saved updated JSON")
        return True
    except Exception as e:
        print(f"  ❌ Failed to save JSON: {str(e)}")
        return False


def process_all_html_files(max_files: Optional[int] = None):
    """
    Process all HTML files and extract data with AI.
    
    Args:
        max_files: Maximum number of files to process (for testing)
    """
    if not HTML_DIR.exists():
        print(f"❌ HTML directory not found: {HTML_DIR}")
        return
    
    html_files = list(HTML_DIR.glob("*.html"))
    
    if not html_files:
        print(f"❌ No HTML files found in {HTML_DIR}")
        return
    
    if max_files:
        html_files = html_files[:max_files]
    
    print(f"📊 Found {len(html_files)} HTML files to process")
    print()
    
    successful = 0
    failed = 0
    
    for i, html_file in enumerate(html_files, 1):
        job_id = html_file.stem
        
        # Load existing JSON if it exists
        json_file = JSON_DIR / f"{job_id}.json"
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_json = json.load(f)
        else:
            print(f"[{i}/{len(html_files)}] ⚠️  No existing JSON for {job_id}, skipping")
            continue
        
        print(f"[{i}/{len(html_files)}] Processing {job_id}...")
        
        success = process_html_file(html_file, existing_json)
        
        if success:
            successful += 1
        else:
            failed += 1
    
    # Print summary
    print()
    print("=" * 60)
    print("📊 AI Extraction Summary")
    print("=" * 60)
    print(f"Total files: {len(html_files)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"Success rate: {(successful/len(html_files)*100):.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    # Check for max files argument
    max_files = None
    if len(sys.argv) > 1:
        try:
            max_files = int(sys.argv[1])
            print(f"🔍 Processing first {max_files} files")
            print()
        except ValueError:
            print("Usage: python extract_with_ai.py [max_files]")
            sys.exit(1)
    
    process_all_html_files(max_files=max_files)
