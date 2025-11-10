# Batch Runner Usage Guide

## Overview

The batch runner (`src/main.py`) allows you to run all Canadian government job scrapers sequentially with a single command. It provides progress tracking, detailed logging, and summary statistics.

## Quick Start

### Run All Scrapers

```bash
python -m src.main
```

This will run all 7 Canadian jurisdiction scrapers in sequence:
1. Government of Canada (Federal)
2. British Columbia
3. Alberta
4. Saskatchewan
5. Manitoba
6. Ontario
7. Nova Scotia

### Run Specific Scrapers

```bash
# Run just Alberta and British Columbia
python -m src.main --jurisdictions AB BC

# Run federal and Ontario only
python -m src.main --jurisdictions GOC ONT
```

### List Available Scrapers

```bash
python -m src.main --list
```

Output:
```
Available scrapers:
------------------------------------------------------------
✓ GOC  - Government of Canada (Federal)
✓ BC   - British Columbia
✓ AB   - Alberta
✓ SAS  - Saskatchewan
✓ MAN  - Manitoba
✓ ONT  - Ontario
✓ NS   - Nova Scotia
------------------------------------------------------------
Total: 7 scrapers
Enabled: 7
```

## Features

### Progress Tracking

The batch runner provides real-time progress updates:

```
[1/7] Running Government of Canada (Federal)...
✓ Government of Canada (Federal) completed successfully
  Jobs in dataset: 27
  Time taken: 12.3 minutes

[2/7] Running British Columbia...
✓ British Columbia completed successfully
  Jobs in dataset: 18
  Time taken: 18.7 minutes
```

### Detailed Logging

Each batch run creates a timestamped log file:

```
logs/batch_run_20251109_143022.log
```

The log contains:
- Start/end timestamps
- Individual scraper progress
- Error messages (if any)
- Summary statistics
- Total jobs collected

### Summary Statistics

At the end of each batch run, you'll see:

```
================================================================================
BATCH RUN SUMMARY
================================================================================
Total scrapers run: 7
Successful: 7
Failed: 0
Total time: 95.4 minutes

Successful runs:
  ✓ Government of Canada (Federal): 27 jobs (12.3 minutes)
  ✓ British Columbia: 18 jobs (18.7 minutes)
  ✓ Alberta: 27 jobs (15.2 minutes)
  ✓ Saskatchewan: 23 jobs (11.8 minutes)
  ✓ Manitoba: 28 jobs (8.3 minutes)
  ✓ Ontario: 21 jobs (13.4 minutes)
  ✓ Nova Scotia: 14 jobs (9.7 minutes)

Total jobs in dataset: 158

End time: 2025-11-09 16:45:12
Log saved to: logs/batch_run_20251109_143022.log
================================================================================
```

## Testing Before Running

Before running a full batch, validate your setup:

```bash
python tests/test_batch_runner.py
```

This pre-flight check will:
- ✓ Test all scraper module imports
- ✓ Verify data directories exist
- ✓ Check configuration files
- ✓ Show current job counts

Expected output:
```
======================================================================
TEST SUMMARY
======================================================================
✓ PASS - Module Imports
✓ PASS - Data Directories
✓ PASS - Configuration
======================================================================

✓ All tests passed! Batch runner is ready.
```

## Command-Line Options

### Full Syntax

```bash
python -m src.main [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--jurisdictions CODE [CODE ...]` | `-j` | Run specific jurisdictions only |
| `--test` | `-t` | Test mode (quick validation) |
| `--list` | `-l` | List available scrapers and exit |
| `--help` | `-h` | Show help message |

### Jurisdiction Codes

| Code | Jurisdiction |
|------|--------------|
| `GOC` | Government of Canada (Federal) |
| `BC` | British Columbia |
| `AB` | Alberta |
| `SAS` | Saskatchewan |
| `MAN` | Manitoba |
| `ONT` | Ontario |
| `NS` | Nova Scotia |

## Examples

### Research Use Cases

**Monthly data collection:**
```bash
# Run all scrapers once per month
python -m src.main
```

**Focus on specific provinces:**
```bash
# Western Canada only
python -m src.main --jurisdictions BC AB SAS MAN

# Central Canada only
python -m src.main --jurisdictions ONT GOC
```

**Test a single scraper:**
```bash
# Just test Alberta
python -m src.main --jurisdictions AB
```

## Expected Runtime

Typical execution times (approximate):

| Jurisdiction | Time | Jobs Collected |
|-------------|------|----------------|
| Government of Canada | ~10-15 min | ~27 |
| British Columbia | ~15-20 min | ~18 |
| Alberta | ~12-18 min | ~27 |
| Saskatchewan | ~10-15 min | ~23 |
| Manitoba | ~8-12 min | ~28 |
| Ontario | ~10-15 min | ~21 |
| Nova Scotia | ~8-12 min | ~14 |
| **Total** | **~90-120 min** | **~158** |

*Times vary based on network speed and current job board activity.*

## Output Files

After running, you'll find:

```
public_jobs_scraper/
├── data/
│   ├── GOC/jobs_json/          ← Federal jobs
│   ├── BC/jobs_json/           ← BC jobs
│   ├── AB/jobs_json/           ← Alberta jobs
│   ├── SAS/jobs_json/          ← Saskatchewan jobs
│   ├── MAN/jobs_json/          ← Manitoba jobs
│   ├── ONT/jobs_json/          ← Ontario jobs
│   └── NS/jobs_json/           ← Nova Scotia jobs
│
└── logs/
    └── batch_run_YYYYMMDD_HHMMSS.log  ← Batch run log
```

## Error Handling

If a scraper fails, the batch runner:
1. ✓ Logs the error
2. ✓ Continues with remaining scrapers
3. ✓ Reports failed scrapers in summary
4. ✓ Exits with error code (for automation)

Example with failures:
```
================================================================================
BATCH RUN SUMMARY
================================================================================
Total scrapers run: 7
Successful: 5
Failed: 2

Failed runs:
  ✗ Ontario: TimeoutError - Page took too long to load
  ✗ Nova Scotia: ConnectionError - Network unavailable
================================================================================
```

## Troubleshooting

### Pre-flight check fails

```bash
# Re-run the test to see specific issues
python tests/test_batch_runner.py
```

### Individual scraper fails

```bash
# Run that scraper alone to see detailed errors
python -m src.AB.ab_scraper  # Example for Alberta
```

### Network timeouts

- Increase timeout in individual scraper configs
- Run fewer scrapers in parallel (use `--jurisdictions`)
- Check your internet connection

### Browser issues

```bash
# Reinstall Playwright browsers
playwright install chromium
```

## Automation

### Cron Job (Monthly)

```bash
# Edit crontab
crontab -e

# Add line to run on 1st of each month at 2 AM
0 2 1 * * cd /path/to/public_jobs_scraper && /path/to/python -m src.main
```

### Shell Script

Create `run_batch.sh`:

```bash
#!/bin/bash
cd /path/to/public_jobs_scraper
source .venv/bin/activate  # If using virtual environment
python -m src.main
```

Make executable:
```bash
chmod +x run_batch.sh
./run_batch.sh
```

## Best Practices

1. **Run during off-peak hours** (late night/early morning)
2. **Check pre-flight** before each batch run
3. **Monitor logs** for patterns in errors
4. **Archive old data** before running fresh collection
5. **Keep keywords updated** in `list-of-jobs.txt`

## Support

For issues with:
- **Batch runner**: Check `tests/test_batch_runner.py`
- **Individual scraper**: Run scraper directly (e.g., `python -m src.AB.ab_scraper`)
- **Configuration**: Verify `list-of-jobs.txt` exists and has content
