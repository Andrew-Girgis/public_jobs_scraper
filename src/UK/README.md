# Nova Scotia Government Job Scraper

Automated scraper for Nova Scotia government job postings from https://jobs.novascotia.ca

## Features

- **Hybrid Search Approach**: Combines keyword search with token-based filtering
  - Uses Nova Scotia's built-in search to find jobs by keyword
  - Applies token matching to filter only relevant jobs (like GOC/ONT)
  - Best of both worlds: efficient search + precise filtering

- **Token-Based Matching (Filter)**: Filters jobs using advanced matching
  - Exact phrase matching (100 points)
  - Multi-token matching (95 points)
  - Single token matching (90 points)
  - Word variation matching (88 points)
  - Pattern matching (85 points)
  - Score of 0 means found via search but no token match

- **Comprehensive Data Extraction**: Extracts 30+ fields including:
  - Job metadata (title, department, location, classification)
  - Content sections (About Us, About Our Opportunity, Primary Accountabilities)
  - Qualifications and experience (education, required skills, assets)
  - Benefits and working conditions
  - Compensation details
  - Application instructions and statements

- **Robust Pagination**: Automatically handles multi-page search results

- **Human-Like Behavior**: Includes random delays and scrolling to avoid bot detection

- **Detailed Logging**: Comprehensive logs saved to `logs/NS/`

## Architecture

The scraper follows the same pattern as GOC and ONT scrapers:

```
src/NS/
├── __init__.py          # Package initialization
├── config.py            # Configuration settings
├── models.py            # NSJob data model
├── parser.py            # Content parsing utilities
└── ns_scraper.py        # Main scraper logic
```

## Usage

### Run the scraper

```bash
python -m src.NS.ns_scraper
```

The scraper will:
1. Load keywords from `list-of-jobs.txt`
2. Search for each keyword on jobs.novascotia.ca
3. Extract matching job listings from all pages
4. Scrape detailed information for each job
5. Save data to JSON files in `data/NS/jobs_json/`

### Output Files

- **JSON Data**: `data/NS/jobs_json/ns_job_{job_id}.json`
- **HTML Archives**: `data/NS/job_html/ns_job_{job_id}.html`
- **Search Results**: `data/NS/search_html/ns_search_{keyword}_{timestamp}.html`
- **Logs**: `logs/NS/ns_scraper_{timestamp}.log`

## Configuration

Edit `src/NS/config.py` to customize:

- `HEADLESS`: Run browser in headless mode (default: False)
- `TIMEOUT`: Page timeout in milliseconds (default: 30000)
- `DELAY_BETWEEN_PAGES`: Delay between page navigations (default: 2s)
- `DELAY_BETWEEN_SEARCHES`: Delay between keyword searches (default: 3s)

## Data Structure

Jobs are saved in the following JSON structure:

```json
{
  "job_posting": {
    "source": {
      "jurisdiction": "Nova Scotia",
      "job_board": "Government of Nova Scotia",
      "url": "https://jobs.novascotia.ca/job/..."
    },
    "metadata": {
      "job_title": "Senior Policy Analyst",
      "classification": "Program Admin Officer 4",
      "department": "Office of Addictions and Mental Health",
      "location": "HALIFAX, NS, CA, B3J2R8",
      "closing_date": "2025-11-23T00:00:00",
      ...
    },
    "about_us": {
      "heading": "About Us",
      "body": "..."
    },
    "qualifications_and_experience": {
      "heading": "Qualifications and Experience",
      "required_education": "...",
      "required_bullets": [...],
      "asset_bullets": [...],
      ...
    },
    "compensation": {
      "pay_grade": "...",
      "salary_range": {
        "raw_text": "$2,345.67 - $3,456.78 Bi-Weekly",
        "min_amount": 2345.67,
        "max_amount": 3456.78,
        "frequency": "Bi-Weekly",
        "currency": "CAD"
      }
    },
    ...
  },
  "scraping_metadata": {
    "job_id": "597235617",
    "scraped_at": "2025-11-09T12:00:00",
    "matched_keyword": "Policy Analyst",
    "match_score": 95.0
  }
}
```

## Matching System

The scraper uses token-based matching to **filter** jobs and only scrape relevant positions.

**How it works:**
1. Search Nova Scotia jobs using each keyword
2. For each result, check if the job title matches ANY keyword from `list-of-jobs.txt`
3. Only scrape jobs that pass the token matching filter
4. This prevents scraping thousands of irrelevant jobs

### Match Scores

| Score | Meaning | Example |
|-------|---------|---------|
| 100 | Exact phrase match | "Senior Policy Analyst" matches "Policy Analyst" |
| 95 | All tokens present | "Data Analyst (Computer Services)" matches "Data Analyst" |
| 90 | Single token match | "Manager, Financial Services" matches "Manager" |
| 88 | Word variation | "Economic Officer" matches "Economist" |
| 85 | Pattern match | "Information Management Specialist" matches "Information Management" |

### Examples

When searching for "Secretary":
- ✓ Scrapes: "Senior Policy Analyst" (matches "Policy Analyst" from keyword list)
- ✓ Scrapes: "Data Analyst" (matches "Data Analyst" from keyword list)
- ✗ Skips: "Electrician" (no match in keyword list)
- ✗ Skips: "Laboratory Assistant" (no match in keyword list)

**Only matching jobs are scraped** - this saves time and focuses on relevant positions.

### Word Variations

The scraper recognizes common word variations:
- economist ↔ economic, economy, economics
- analyst ↔ analysis, analytical
- manager ↔ management, managing
- developer ↔ development, developing
- administrator ↔ administration, administrative
- coordinator ↔ coordination, coordinating

## Requirements

- Python 3.8+
- playwright
- rapidfuzz (imported but not used - kept for compatibility)

Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

## Troubleshooting

### No jobs found
- Check if keywords are relevant to Nova Scotia government jobs
- Verify the website structure hasn't changed
- Check logs in `logs/NS/` for details

### Browser issues
- Ensure Playwright browsers are installed: `playwright install chromium`
- Try running with `HEADLESS = False` to see browser actions
- Check firewall/proxy settings

### Timeout errors
- Increase `TIMEOUT` in `config.py`
- Check internet connection
- Try running during off-peak hours

## Integration with Database

To upload scraped jobs to Supabase (similar to GOC and ONT scrapers):

1. Create a database table using the schema from the JSON structure
2. Create an upload script similar to `src/ONT/upload_ont_jobs.py`
3. Configure `.env` with Supabase credentials
4. Run the upload script

## Logging

All scraping activity is logged to:
- Console output (INFO level)
- Log file in `logs/NS/` (DEBUG level)

Log format:
```
🔍 Searching for: 'Data Analyst'
  📄 Total pages: 2
📄 Processing page 1/2
  📋 Found 25 jobs on this page
  ✓ MATCH: 'Senior Policy Analyst' → 'Policy Analyst' (score: 100)
  ✓ MATCH: 'Senior Cyber and Risk Analyst' → 'Data Analyst' (score: 95)
  ✗ No match: 'Capital Markets Officer'
  ✗ No match: 'Secretary 3'
  ✓ Extracted 2 matching jobs from page
✓ Page 1/2: Found 2 matching jobs
📄 Processing page 2/2
  📋 Found 1 jobs on this page
  ✓ MATCH: 'Technical Analyst' → 'Data Analyst' (score: 90)
  ✓ Extracted 1 matching jobs from page
✓ Page 2/2: Found 1 matching jobs
✓ Total matching jobs for 'Data Analyst': 3
```

## Notes

- The scraper respects the website by including human-like delays
- HTML files are saved for debugging and verification
- Search results are cached to avoid duplicate requests
- The scraper handles pagination automatically
- Jobs are deduplicated by job_id

## Comparison with Other Scrapers

| Feature | GOC | ONT | NS |
|---------|-----|-----|-----|
| Token Matching | ✓ | ✓ | ✓ |
| Word Variations | ✓ | ✓ | ✓ |
| Human-like Behavior | ✓ | ✓ | ✓ |
| Pagination | ✓ | ✓ | ✓ |
| JSON Output | ✓ | ✓ | ✓ |
| HTML Archives | ✓ | ✓ | ✓ |
| Detailed Logging | ✓ | ✓ | ✓ |
| URL-based Search | ✓ | ✗ | ✓ |
| Form-based Search | ✗ | ✓ | ✗ |

## Future Enhancements

- [ ] Database upload script (Supabase integration)
- [ ] Enhanced content parsing for nested bullet points
- [ ] Email notifications for new matching jobs
- [ ] Batch mode for scheduled scraping
- [ ] Dashboard for viewing scraped jobs
- [ ] Duplicate detection across provinces
