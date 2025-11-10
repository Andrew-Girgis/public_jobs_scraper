# Ontario (ONT) Public Service Job Scraper

This scraper collects job postings from the Ontario Public Service careers website (https://www.gojobs.gov.on.ca) that match keywords from your job list.

## How It Works

### Architecture

Unlike the Government of Canada scraper which searches by keyword, the Ontario scraper:

1. **Loads job keywords** from `list-of-jobs.txt`
2. **Iterates through all search result pages** on the base job page
3. **Performs fuzzy matching** on each job title against your keywords
4. **Saves matching job links** for later detailed scraping
5. **Visits each matched job** and extracts complete details
6. **Saves data as JSON** in `data/ONT/jobs_json/`

### Fuzzy Matching

The scraper uses **RapidFuzz** for intelligent title matching:
- **Token sort ratio**: Handles different word orders (e.g., "Data Analyst Junior" matches "Junior Data Analyst")
- **Configurable threshold**: Default 80% match score (adjustable in `config.py`)
- **Best match selection**: Automatically finds the best matching keyword for each job

## Project Structure

```
src/ONT/
├── __init__.py          # Package marker
├── config.py            # Configuration settings
├── models.py            # Data models (OntJob, JobMatch)
├── parser.py            # Parsing utilities
└── ont_scraper.py       # Main scraper logic
```

## Configuration

Edit `src/ONT/config.py` to customize:

```python
# Scraping settings
HEADLESS = True                    # Run browser in headless mode
TIMEOUT = 30000                    # Page timeout (milliseconds)
DELAY_BETWEEN_PAGES = 2            # Delay between page requests (seconds)

# Fuzzy matching settings
FUZZY_MATCH_THRESHOLD = 80         # Minimum match score (0-100)
```

## Usage

### Standalone Mode

Run the scraper directly:

```bash
# From project root
python -m src.ONT.ont_scraper
```

### As Part of Batch Scraper

Import and call from `src/main.py`:

```python
from src.ONT.ont_scraper import main as run_ont_scraper

# Run Ontario scraper
run_ont_scraper()
```

## Data Structure

### OntJob Model

Each job is saved with the following structure:

```json
{
  "job_id": "235707",
  "url": "https://www.gojobs.gov.on.ca/Preview.aspx?Language=English&JobID=235707",
  "title": "Regional Information Management Specialist",
  "organization": "Ministry of Natural Resources",
  "division": "Regional Operations Division, Northeast Region",
  "city": "South Porcupine",
  "posting_status": "Open",
  "position_language": "English",
  "job_term": "1 Permanent",
  "job_code": "17158 - Systems Officer 4",
  "salary": "$1,512.75  - $1,933.38 Per week*",
  "salary_min": 1512.75,
  "salary_max": 1933.38,
  "salary_period": "week",
  "apply_by": "2025-11-21T23:59:00",
  "posted_on": "2025-11-06T00:00:00",
  "position_details": "1 English Permanent, 5520 Hwy 101 E, South Porcupine, North Region",
  "compensation_group": "Ontario Public Service Employees Union",
  "work_hours": "Schedule 6",
  "category": "Information Technology",
  "note": "T-NR-235707/25",
  "about_the_job": "...",
  "what_you_bring": "...",
  "mandatory_requirements": "...",
  "additional_info": "...",
  "how_to_apply": "...",
  "scraped_at": "2025-11-08T10:30:00",
  "matched_keyword": "Information Management Specialist",
  "match_score": 95.5
}
```

## Output Files

### JSON Files
- **Location**: `data/ONT/jobs_json/`
- **Format**: `ont_job_{job_id}.json`
- **Content**: Complete job posting data

### HTML Files
- **Job pages**: `data/ONT/job_html/job_{job_id}_{timestamp}.html`
- **Search pages**: `data/ONT/search_html/search_page_{page_num}_{timestamp}.html`
- **Purpose**: Debugging and verification

### Log Files
- **Location**: `logs/ONT/`
- **Format**: `ont_scraper_{timestamp}.log`
- **Content**: Detailed scraping activity

## Dependencies

Required Python packages:
- `playwright` - Browser automation
- `rapidfuzz` - Fuzzy string matching

Install with:
```bash
pip install playwright rapidfuzz
playwright install chromium
```

## Troubleshooting

### No jobs found
1. Check `list-of-jobs.txt` has job keywords
2. Lower `FUZZY_MATCH_THRESHOLD` in `config.py` (try 70)
3. Check logs in `logs/ONT/` for details

### Page navigation errors
1. Increase `TIMEOUT` in `config.py`
2. Increase `DELAY_BETWEEN_PAGES` to be more polite
3. Set `HEADLESS = False` to see what's happening

### HTML structure changed
1. Check saved HTML files in `data/ONT/job_html/`
2. Update selectors in `ont_scraper.py`
3. Test parsing with a single job first

## Best Practices

### Respectful Scraping
- Default 2-second delay between requests
- Proper user agent via Playwright
- Handles errors gracefully
- Saves pages for debugging (don't re-scrape)

### Extensibility
- Clean separation of concerns (models, config, parser, scraper)
- Can run standalone or as module
- Easy to modify selectors and logic
- Comprehensive logging

## Future Enhancements

Potential improvements:
- [ ] Resume scraping from last position
- [ ] Incremental updates (only scrape new jobs)
- [ ] Database integration (like Supabase for GOC)
- [ ] Email notifications for new matches
- [ ] Advanced filtering (by location, salary, etc.)

## Testing

Test with a small number of keywords first:

1. Create a test keyword file:
```bash
echo "Data Analyst\nProject Manager" > list-of-jobs-test.txt
```

2. Update `config.py` to use test file:
```python
JOB_LIST_FILE = PROJECT_ROOT / "list-of-jobs-test.txt"
```

3. Run with visible browser:
```python
HEADLESS = False
```

4. Check output in `data/ONT/jobs_json/`
