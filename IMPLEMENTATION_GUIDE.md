# GOC Jobs Scraper - Unified Implementation Guide

This document provides a complete implementation guide for updating the GOC job scraper
to support three page structures using a unified data model.

## Files Created

1. **`src/GOC/models.py`** ✅ COMPLETE
   - Unified `GocJob` data model
   - All nested models (JobDetails, Sections, Qualifications, Contact, etc.)
   - `.to_dict()` methods for JSON serialization

2. **`src/GOC/goc_jobs_schema.sql`** ✅ COMPLETE
   - PostgreSQL schema for Supabase
   - Indexes for performance
   - Example upsert pattern
   - Documentation comments

3. **`src/GOC/goc_scraper.py`** ⚠️ NEEDS IMPLEMENTATION
   - Backup saved as `goc_scraper_backup.py`
   - See implementation steps below

## Implementation Steps for goc_scraper.py

### Step 1: Add imports at the top

```python
from .models import (
    GocJob, JobDetails, Sections, Qualifications, QualificationBlock,
    Contact, ContactInfo
)
```

### Step 2: Add structure detection function

```python
def detect_structure_type(page: Page) -> str:
    """
    Detect which page structure type the current job posting uses.
    
    Returns:
        'structure_1', 'structure_2', or 'external_redirect'
    """
    try:
        # Check for external redirect first
        h1_elem = page.query_selector("h1")
        if h1_elem:
            h1_text = clean_text(h1_elem.inner_text())
            if "you will leave the gc jobs web site" in h1_text.lower():
                return "external_redirect"
        
        # Check for Structure 1 (has "On this page" navigation)
        if page.query_selector("text='On this page'"):
            return "structure_1"
        
        # Check for Structure 2 (has rightRefNumberWithPadding)
        if page.query_selector("div.rightRefNumberWithPadding"):
            return "structure_2"
        
        # Check for Structure 2 via fieldset
        if page.query_selector("fieldset div.text-center"):
            return "structure_2"
        
        return "structure_1"  # default
    except Exception as e:
        logger.error(f"Error detecting structure type: {e}")
        return "structure_1"
```

### Step 3: Create structure-specific parsers

#### A. External Redirect Parser (SIMPLEST)

```python
def parse_external_redirect(page: Page, url: str, poster_id: str,
                           search_title: str, search_type: str,
                           scraped_at: datetime) -> GocJob:
    """
    Parse an external redirect page.
    
    These pages show "You will leave the GC Jobs Web site" and have a single
    external link to another job board.
    """
    # Get the external link
    external_url = ""
    external_title = ""
    
    try:
        main_elem = page.query_selector("main")
        if main_elem:
            link = main_elem.query_selector("a[href^='http']")
            if link:
                external_url = link.get_attribute('href') or ""
                external_title = clean_text(link.inner_text())
    except Exception as e:
        logger.error(f"Error extracting external link: {e}")
    
    # Get date_modified if available
    date_modified = None
    try:
        date_elem = page.query_selector("dl#wb-dtmd dd time")
        if date_elem:
            date_text = clean_text(date_elem.inner_text())
            date_modified = parse_date_string(date_text)
    except Exception:
        pass
    
    return GocJob(
        poster_id=poster_id,
        url=url,
        title="You will leave the GC Jobs Web site",
        is_external_link=True,
        external_redirect_url=external_url,
        external_job_title=external_title,
        search_title=search_title,
        search_type=search_type,
        scraped_at=scraped_at,
        structure_type="external_redirect",
        date_modified=date_modified,
        details=JobDetails()
    )
```

#### B. Structure 2 Parser (USE EXISTING CODE)

```python
def parse_structure_2(page: Page, url: str, poster_id: str,
                     search_title: str, search_type: str,
                     scraped_at: datetime) -> GocJob:
    """
    Parse a Structure 2 (classic layout) job posting.
    
    Classic layout uses:
    - <h1>Title</h1>
    - <div class="rightRefNumberWithPadding"> for ref numbers
    - Centered fieldset for basic info
    - <h2> sections for content
    """
    # THIS IS YOUR EXISTING CODE FROM THE ALTERNATE FORMAT!
    # Just wrap it in GocJob format
    
    # Use your existing extract_alternate_* functions
    title = clean_text(page.query_selector("h1").inner_text()) if page.query_selector("h1") else None
    
    ref_num = extract_alternate_reference_number(page)
    sel_proc = extract_alternate_selection_process(page)
    dept = extract_alternate_department(page)
    location_raw = extract_alternate_location(page)
    city, province = parse_location(location_raw) if location_raw else (None, None)
    
    salary_raw = extract_alternate_salary(page)
    salary_min, salary_max = parse_salary(salary_raw) if salary_raw else (None, None)
    
    classification_raw = extract_alternate_classification(page)
    class_group, class_level = parse_classification(classification_raw) if classification_raw else (None, None)
    
    closing_raw = extract_alternate_closing_date(page)
    closing_date = parse_date_string(closing_raw) if closing_raw else None
    
    who_can_apply = extract_alternate_who_can_apply(page)
    positions_raw = extract_alternate_positions_to_fill(page)
    positions_to_fill = parse_positions_to_fill(positions_raw) if positions_raw else None
    
    language_req = extract_alternate_language_requirements(page)
    
    # Extract employment types from fieldset
    employment_types = None
    try:
        fieldset = page.query_selector("fieldset div.text-center")
        if fieldset:
            text = fieldset.inner_text()
            if re.search(r'(Acting|Assignment|Deployment|Indeterminate)', text):
                match = re.search(r'(Acting[^$<\n]*)', text)
                if match:
                    employment_types = clean_text(match.group(1))
    except Exception:
        pass
    
    # Build details using existing extract functions
    sections = Sections(
        reference_number=ref_num,
        selection_process_number=sel_proc,
        work_environment=extract_section_by_heading_alternate(page, "Work environment"),
        duties=extract_section_by_heading_alternate(page, "Duties"),
        important_messages=extract_section_by_heading_alternate(page, "Important messages"),
        intent_of_process=extract_section_by_heading_alternate(page, "Intent of the process"),
        conditions_of_employment=extract_section_by_heading_alternate(page, "Conditions of employment"),
        other_information=extract_section_by_heading_alternate(page, "Other information"),
        preference=extract_section_by_heading_alternate(page, "Preference")
    )
    
    # Build qualifications using existing extract functions
    essential = QualificationBlock(
        education=[extract_requirement_block_alternate(page, "EDUCATION", "essential")],
        experience=[extract_requirement_block_alternate(page, "EXPERIENCE", "essential")],
        knowledge=[extract_requirement_block_alternate(page, "KNOWLEDGE", "essential")],
        abilities=[extract_requirement_block_alternate(page, "ABILITY", "essential")],
        personal_suitability=[extract_requirement_block_alternate(page, "PERSONAL SUITABILITY", "essential")]
    )
    
    asset = QualificationBlock(
        experience=[extract_requirement_block_alternate(page, "EXPERIENCE", "asset")]
    )
    
    qualifications = Qualifications(essential=essential, asset=asset)
    
    # Extract contact
    contact_info = extract_section_by_heading_alternate(page, "Contact information")
    contacts = []
    if contact_info:
        # Simple parsing - you can enhance this
        contact = ContactInfo(notes=contact_info)
        contacts.append(contact)
    
    contact = Contact(contacts=contacts)
    
    details = JobDetails(
        sections=sections,
        qualifications=qualifications,
        contact=contact
    )
    
    return GocJob(
        poster_id=poster_id,
        url=url,
        title=title,
        department=dept,
        city=city,
        province=province,
        location_raw=location_raw,
        classification_group=class_group,
        classification_level=class_level,
        classification_raw=classification_raw,
        closing_date=closing_date,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_raw=salary_raw,
        who_can_apply=who_can_apply,
        employment_types=employment_types,
        positions_to_fill=positions_to_fill,
        language_requirements_raw=language_req,
        is_external_link=False,
        search_title=search_title,
        search_type=search_type,
        scraped_at=scraped_at,
        structure_type="structure_2",
        details=details
    )
```

#### C. Structure 1 Parser (NEW - NEEDS IMPLEMENTATION)

This is the new modern layout. You'll need to implement extraction functions similar to what you have for Structure 2, but targeting the different selectors.

Key selectors for Structure 1:
- Title: `h1 span.no-break-word`
- Department: `h2.pst-h2` (split on `-`)
- Closing date: In `h3.pst-h3 p.text-success`
- Reference/Selection #: In left "well" box with `<b>` labels
- Location, Salary, Classification: Also in left well
- Sections: Use `<div id="...">` selectors like `#aboutPosition`, `#youNeed`, etc.

### Step 4: Update main parsing function

Replace the old `parse_job_details` with:

```python
def parse_job_page(page: Page, job_url: str, poster_id: str,
                   search_title: str, search_type: str) -> GocJob:
    """
    Main entry point for parsing a job page.
    
    Detects structure type and routes to appropriate parser.
    """
    scraped_at = datetime.now(timezone.utc)
    
    # Detect structure
    structure_type = detect_structure_type(page)
    logger.info(f"Detected {structure_type} for poster {poster_id}")
    
    # Route to appropriate parser
    if structure_type == "external_redirect":
        return parse_external_redirect(page, job_url, poster_id, 
                                      search_title, search_type, scraped_at)
    elif structure_type == "structure_2":
        return parse_structure_2(page, job_url, poster_id,
                                search_title, search_type, scraped_at)
    else:  # structure_1
        return parse_structure_1(page, job_url, poster_id,
                                search_title, search_type, scraped_at)
```

### Step 5: Update the main workflow

In `fetch_and_parse_job`, replace the dict-based code with:

```python
def fetch_and_parse_job(page: Page, job_url: str, query: str) -> Optional[GocJob]:
    """Fetch and parse a single job posting."""
    poster_id = extract_poster_id(job_url)
    if not poster_id:
        logger.warning(f"Could not extract poster_id from {job_url}")
        return None
    
    try:
        logger.info(f"Scraping job {poster_id} from {job_url}")
        page.goto(job_url, wait_until="domcontentloaded", timeout=JOB_TIMEOUT)
        
        # Wait for network idle
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PWTimeout:
            logger.debug(f"Network not idle after 10s for {job_url}")
        
        # Save raw HTML
        job_html = page.content()
        save_job_html(job_html, poster_id)
        
        # Parse using unified model
        job = parse_job_page(page, job_url, poster_id, query, "production")
        
        logger.info(f"Parsed job {poster_id} — '{job.title}' ({job.structure_type})")
        
        # Save JSON
        save_job_json(job)
        
        return job
    
    except Exception as e:
        logger.error(f"Error scraping job {job_url}: {e}", exc_info=True)
        return None
```

## Quick Start

1. **Restore your backup:**
   ```bash
   cp src/GOC/goc_scraper_backup.py src/GOC/goc_scraper.py
   ```

2. **Add the new import** at the top (after playwright imports)

3. **Add `detect_structure_type()` function**

4. **Add `parse_external_redirect()` function** (copy from guide above)

5. **Rename your existing alternate format code:**
   - Keep all your `extract_alternate_*` functions as-is
   - Wrap them in `parse_structure_2()` as shown above

6. **Create `parse_job_page()` dispatcher function**

7. **Update `fetch_and_parse_job()` to use GocJob**

8. **Implement `parse_structure_1()` when you encounter Structure 1 jobs**

## Testing

Test each structure type individually:

```python
# Test external redirect
python -c "from src.GOC.goc_scraper import *; test_job('2370123')"  # Use an external redirect poster_id

# Test structure 2 (classic)
python -c "from src.GOC.goc_scraper import *; test_job('2037132')"  # Use the Program Officer example

# Test structure 1 (new layout)
python -c "from src.GOC.goc_scraper import *; test_job('2370982')"  # Use Junior Data Analyst example
```

## Database Integration

Once scraping works, implement `upload_to_supabase(job: GocJob)` using the Supabase Python client and the upsert pattern from the SQL schema file.

---

**Note:** Your existing code for Structure 2 (alternate format) is already 90% there! You just need to wrap it in the GocJob model. Structure 1 will require new extraction functions, but follow the same pattern.
