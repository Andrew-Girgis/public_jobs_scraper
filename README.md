# Canadian Government Job Scraper

Automated job scraping system for Canadian government job boards across multiple jurisdictions.

## Overview

This project provides a unified scraping architecture for extracting job postings from various Canadian government job portals. Each scraper uses token-based matching to identify relevant positions based on a customizable keyword list.

## Supported Jurisdictions

| Jurisdiction | Status | Website | Search Method |
|--------------|--------|---------|---------------|
| **Government of Canada (GOC)** | ✅ Complete | https://www.canada.ca/en/services/jobs/opportunities/government.html | Browse all + filter |
| **Ontario (ONT)** | ✅ Complete | https://www.gojobs.gov.on.ca | Browse all + filter |
| **Nova Scotia (NS)** | ✅ Ready | https://jobs.novascotia.ca | Keyword search + filter |

### Search Method Differences

**Browse + Filter (GOC, ONT)**:
- No keyword search available on the website
- Scraper retrieves all jobs, then filters by keywords using token matching
- Only matching jobs are scraped in detail

**Search + Filter (NS)**:
- Website provides keyword search functionality
- Scraper searches each keyword, then filters results using token matching
- Hybrid approach: efficient search + precise filtering
- Only matching jobs are scraped in detail

## Features

### Token-Based Matching System
All scrapers use an advanced 5-tier matching algorithm:

1. **Exact Phrase Match (100 points)**: Keyword appears as substring
   - "Senior Policy Analyst" matches "Policy Analyst"

2. **Multi-Token Match (95 points)**: All keyword tokens present
   - "Data Analyst" matches "Senior Data Analyst"

3. **Single Token Match (90 points)**: Single keyword token present
   - "Manager" matches "Manager, Financial Services"

4. **Word Variation Match (88 points)**: Recognized variations
   - "Economist" matches "Economic Officer"
   - "Analyst" matches "Analysis Specialist"

5. **Pattern Match (85 points)**: Common role combinations
   - "Information Management" matches "Information Management Specialist"

### Word Variations Dictionary
```python
economist ↔ economic, economy, economics
analyst ↔ analysis, analytical
manager ↔ management, managing
developer ↔ development, developing
administrator ↔ administration, administrative
coordinator ↔ coordination, coordinating
officer ↔ official
advisor ↔ advisory, advising
```

### Common Features

- **Human-Like Behavior**: Random delays, smooth scrolling, varied interactions
- **Comprehensive Logging**: Detailed logs with timestamps and progress tracking
- **Data Preservation**: Saves both JSON and HTML archives
- **Pagination Handling**: Automatic multi-page result processing
- **Error Recovery**: Graceful handling of timeouts and failures
- **Duplicate Prevention**: Job ID-based deduplication

## Project Structure

```
public_jobs_scraper/
├── data/
│   ├── GOC/
│   │   ├── jobs_json/      # JSON output files
│   │   ├── job_html/       # HTML archives
│   │   └── search_html/    # Search result pages
│   ├── ONT/
│   │   └── (same structure)
│   └── NS/
│       └── (same structure)
├── logs/
│   ├── GOC/                # Scraper logs
│   ├── ONT/
│   └── NS/
├── src/
│   ├── GOC/
│   │   ├── config.py
│   │   ├── goc_scraper.py
│   │   ├── models.py
│   │   ├── parser.py
│   │   └── upload_to_supabase.py
│   ├── ONT/
│   │   ├── config.py
│   │   ├── ont_scraper.py
│   │   ├── models.py
│   │   ├── parser.py
│   │   ├── upload_ont_jobs.py
│   │   └── ont_jobs_schema.sql
│   └── NS/
│       ├── config.py
│       ├── ns_scraper.py
│       ├── models.py
│       ├── parser.py
│       └── README.md
├── list-of-jobs.txt        # Keywords to search
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Setup

1. Clone the repository
```bash
cd /path/to/public_jobs_scraper
```

2. Install Python dependencies
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers
```bash
playwright install chromium
```

4. Configure keywords
Edit `list-of-jobs.txt` to customize job search keywords:
```
Data Analyst
Policy Analyst
Project Manager
...
```

## Usage

### Run Individual Scrapers

**Government of Canada:**
```bash
python -m src.GOC.goc_scraper
```

**Ontario:**
```bash
python -m src.ONT.ont_scraper
```

**Nova Scotia:**
```bash
python -m src.NS.ns_scraper
```

### Configuration

Each scraper has a `config.py` file with customizable settings:

```python
HEADLESS = False              # Show/hide browser
TIMEOUT = 30000              # Page timeout (ms)
DELAY_BETWEEN_PAGES = 2      # Delay between pages (s)
DELAY_BETWEEN_SEARCHES = 3   # Delay between keywords (s)
```

### Output

Each scraper produces:

**JSON Files** (`data/{jurisdiction}/jobs_json/`):
```json
{
  "job_posting": {
    "source": {...},
    "metadata": {...},
    "content": {...}
  },
  "scraping_metadata": {
    "job_id": "...",
    "matched_keyword": "...",
    "match_score": 95.0,
    "scraped_at": "2025-11-09T12:00:00"
  }
}
```

**HTML Archives** (`data/{jurisdiction}/job_html/`):
- Full page HTML for verification and debugging

**Logs** (`logs/{jurisdiction}/`):
```
[2025-11-09 12:00:00] INFO: 🔍 Searching for: 'Data Analyst'
[2025-11-09 12:00:01] INFO:   📋 Found 26 jobs on this page
[2025-11-09 12:00:02] INFO:   ✓ MATCH: 'Senior Data Analyst' → 'Data Analyst' (score: 100)
```

## Database Integration

### Ontario Jobs (Supabase)

1. Create database table:
```bash
# Run SQL from src/ONT/ont_jobs_schema.sql
```

2. Configure environment:
```bash
# Create .env file
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

3. Upload jobs:
```bash
# Dry run to validate
python src/ONT/upload_ont_jobs.py --dry-run

# Upload all jobs
python src/ONT/upload_ont_jobs.py

# Upload first 5 jobs
python src/ONT/upload_ont_jobs.py --limit 5
```

### GOC Jobs (Supabase)

Similar process using `src/GOC/upload_to_supabase.py`

## Keywords List

The `list-of-jobs.txt` file contains 43 keywords covering:

**Analysis Roles:**
- Business Analyst
- Data Analyst
- Policy Analyst
- Research Analyst

**Management Roles:**
- Manager
- Project Manager
- Senior Manager

**Technical Roles:**
- Database Administrator
- Network Administrator
- IT Analyst

**Specialized Roles:**
- Economist
- Finance Officer
- Information Officer

**Emerging Fields:**
- Artificial Intelligence
- Machine Learning
- Data Science
- Data Visualization

## Results Summary

### Ontario (ONT)
- **Last Run**: Successfully uploaded
- **Jobs Found**: 14 unique positions
- **Match Breakdown**:
  - 8 Managers (88-100% match)
  - 1 Policy Advisor (100%)
  - 1 Information Management Specialist (85%)
  - 1 Economic Officer (88%)
  - 3 Other matching positions
- **Pages Scraped**: 14/14
- **Status**: ✅ Production Ready

### Nova Scotia (NS)
- **Status**: ✅ Scraper Built & Ready
- **Search Method**: Keyword search + token filtering (hybrid approach)
- **Token Matching**: Used as filter to scrape only relevant jobs
- **Expected Results**: 5-15 matching jobs per keyword
- **Features**: URL-based search, token filtering, pagination, human-like behavior
- **Advantage**: Combines efficient search with precise filtering

## Troubleshooting

### No Jobs Found

1. **Check keywords**: Ensure keywords are relevant to government jobs
2. **Verify website**: Check if site structure has changed
3. **Review logs**: Check `logs/{jurisdiction}/` for details
4. **Test matching**: Use `--debug` mode to see matching scores

### Browser Issues

1. **Install browsers**: `playwright install chromium`
2. **Disable headless**: Set `HEADLESS = False` in config
3. **Check firewall**: Verify proxy/firewall settings
4. **Update Playwright**: `pip install --upgrade playwright`

### Timeout Errors

1. **Increase timeout**: Set `TIMEOUT = 60000` in config
2. **Check connection**: Verify internet stability
3. **Run off-peak**: Try during non-business hours
4. **Reduce parallelism**: Scrape one keyword at a time

## Development

### Adding a New Jurisdiction

1. Create new directory structure:
```bash
mkdir -p src/NEW_JURISDICTION/{config,models,scraper,parser}.py
mkdir -p data/NEW_JURISDICTION/{jobs_json,job_html,search_html}
mkdir -p logs/NEW_JURISDICTION
```

2. Copy template from existing scraper (ONT or NS recommended)

3. Update URLs and selectors in config

4. Implement jurisdiction-specific parsing in parser.py

5. Test with `--dry-run` mode

### Running Tests

```bash
# Test keyword loading
python -c "from src.NS.ns_scraper import load_keywords; print(load_keywords())"

# Test token matching
python -c "from src.NS.ns_scraper import token_match_title, load_keywords; print(token_match_title('Data Analyst', load_keywords()))"

# Test imports
python -c "from src.NS.models import NSJob; print(NSJob.__name__)"
```

## Dependencies

```
playwright>=1.40.0       # Browser automation
rapidfuzz>=3.5.0        # Fuzzy matching (legacy)
supabase>=2.0.0         # Database integration
python-dotenv>=1.0.0    # Environment variables
```

## Performance

| Metric | GOC | ONT | NS |
|--------|-----|-----|-----|
| Keywords | 43 | 43 | 43 |
| Avg Jobs/Keyword | 5-10 | 0-5 | TBD |
| Pages/Keyword | 1-5 | 1-14 | 1-10 |
| Time/Job | 3-5s | 4-6s | 3-5s |
| Total Runtime | ~1hr | ~30min | TBD |

## Best Practices

### Scraping Ethics

- ✅ Respect robots.txt
- ✅ Use human-like delays (2-4 seconds)
- ✅ Limit concurrent requests (1 at a time)
- ✅ Identify with realistic User-Agent
- ✅ Run during off-peak hours
- ✅ Cache results to avoid re-scraping

### Data Management

- ✅ Save both JSON and HTML
- ✅ Include timestamps in filenames
- ✅ Use job IDs for deduplication
- ✅ Version control schema changes
- ✅ Backup data regularly
- ✅ Archive old data

### Error Handling

- ✅ Log all errors with context
- ✅ Continue on individual job failures
- ✅ Retry on network timeouts
- ✅ Validate data before saving
- ✅ Alert on critical failures

## License

This project is for educational and personal use. Respect the terms of service of each government job board.

## Contributing

1. Follow existing scraper patterns (ONT/NS architecture)
2. Use token-based matching system
3. Include comprehensive logging
4. Save JSON + HTML archives
5. Document configuration options
6. Test with multiple keywords
7. Handle pagination properly
8. Add human-like delays

## Changelog

### 2025-11-09
- ✅ Created Nova Scotia (NS) scraper
- ✅ Implemented token-based matching
- ✅ Added word variation dictionary
- ✅ Created parser module for NS
- ✅ Set up directory structure
- ✅ Added comprehensive documentation

### Previous
- ✅ Built Ontario (ONT) scraper
- ✅ Created Supabase integration
- ✅ Implemented token matching for ONT
- ✅ Fixed pagination issues (14 pages)
- ✅ Successfully uploaded 14 jobs to database
- ✅ Completed GOC scraper

## Support

For issues or questions:
1. Check scraper-specific README in `src/{jurisdiction}/`
2. Review logs in `logs/{jurisdiction}/`
3. Test with `HEADLESS = False` to observe behavior
4. Verify website structure hasn't changed

## Roadmap

- [ ] Complete NS scraper testing
- [ ] Add British Columbia (BC) scraper
- [ ] Add United Kingdom (UK) scraper
- [ ] Create unified batch scraper
- [ ] Build web dashboard for results
- [ ] Implement email notifications
- [ ] Add duplicate detection across provinces
- [ ] Create scheduling system (cron jobs)
- [ ] Add data analytics module
