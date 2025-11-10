# Nova Scotia Jobs - Supabase Integration

This directory contains the database schema and upload script for storing Nova Scotia government job postings in Supabase.

## Files

- `ns_jobs_schema.sql` - PostgreSQL schema for the `ns_jobs` table
- `upload_to_supabase.py` - Python script to upload jobs from JSON files to Supabase

## Database Schema

The `ns_jobs` table includes:

### Core Fields
- **job_id** - Unique identifier (Primary Key)
- **job_title** - Job title
- **department** - Government department
- **location** - Job location
- **closing_date** - Application closing date
- **url** - Link to original job posting

### Compensation
- **pay_grade** - Pay grade (e.g., "EC 11")
- **salary_min/max** - Salary range in CAD
- **salary_frequency** - Pay frequency (e.g., "Bi-Weekly")

### Content Sections (Full Text)
- About Us
- About Our Opportunity  
- Primary Accountabilities
- Qualifications and Experience
- Benefits
- Working Conditions
- Additional Information
- What We Offer

### JSONB Arrays
- `primary_accountabilities_bullets`
- `qualifications_required_bullets`
- `qualifications_additional_skills_bullets`
- `qualifications_asset_bullets`
- `what_we_offer_bullets`

### Scraping Metadata
- **search_keyword** - The keyword used in the search query
- **matched_keyword** - The keyword from list-of-jobs.txt that matched
- **match_score** - Token matching score (0-100)
- **scraped_at** - When the job was scraped

### Indexes
- Primary key on `job_id`
- Indexes on common query fields (title, department, location, dates)
- Full-text search indexes on title and content fields

## Setup

### 1. Create Table in Supabase

1. Log in to your [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to **SQL Editor**
4. Copy and paste the contents of `ns_jobs_schema.sql`
5. Click **Run** to create the table

### 2. Configure Environment Variables

Add your Supabase credentials to `.env` file in the project root:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
```

**Note:** Use the `service_role` key for backend scripts (never expose in frontend).

### 3. Install Python Dependencies

The upload script requires the Supabase Python client:

```bash
pip install supabase python-dotenv
```

## Usage

### Dry Run (Validate Without Uploading)

Test the upload script and validate your JSON files:

```bash
python -m src.NS.upload_to_supabase --dry-run
```

This will:
- Load all `ns_job_*.json` files
- Validate the JSON structure
- Transform data to database format
- Report any errors
- **NOT upload** anything to Supabase

### Upload Jobs to Supabase

Upload all jobs to the database:

```bash
python -m src.NS.upload_to_supabase
```

This will:
- Load all NS job JSON files from `data/NS/jobs_json/`
- Transform each job to the database schema
- **Upsert** jobs (insert new, update existing based on `job_id`)
- Display progress and summary

### Example Output

```
================================================================================
Nova Scotia Jobs Uploader
================================================================================
Found 14 job files

📤 Uploading to Supabase...
✓ Uploaded job 597112117: Category Manager (Manager, Strategic Sourcing)
✓ Uploaded job 596820517: Executive Director, Tax, Economics and Fiscal Policy
✓ Uploaded job 596949917: Provincial Coordination Centre Watch Supervisor
...

================================================================================
Upload Complete
================================================================================
✓ Successfully uploaded: 14
✗ Failed: 0
📊 Total: 14
================================================================================
```

## Querying the Data

### Example Queries

**Get all jobs closing after today:**
```sql
SELECT job_id, job_title, department, closing_date
FROM ns_jobs
WHERE closing_date > NOW()
ORDER BY closing_date;
```

**Search jobs by keyword:**
```sql
SELECT job_id, job_title, department, salary_min, salary_max
FROM ns_jobs
WHERE to_tsvector('english', job_title || ' ' || COALESCE(about_us_body, '')) 
      @@ to_tsquery('english', 'manager & procurement');
```

**Get jobs by matched keyword:**
```sql
SELECT job_title, matched_keyword, match_score
FROM ns_jobs
WHERE matched_keyword = 'Policy Analyst'
ORDER BY match_score DESC;
```

**Get salary statistics by department:**
```sql
SELECT 
    department,
    COUNT(*) as job_count,
    AVG(salary_min) as avg_min_salary,
    AVG(salary_max) as avg_max_salary
FROM ns_jobs
WHERE salary_min IS NOT NULL
GROUP BY department
ORDER BY avg_max_salary DESC;
```

## Row Level Security (RLS)

The schema includes commented-out RLS policies. To enable:

1. Uncomment the RLS lines in `ns_jobs_schema.sql`
2. Adjust policies based on your authentication needs
3. Run the SQL in Supabase

Example policies included:
- Public read access
- Authenticated insert/update access

## Data Updates

The upload script uses **UPSERT** on `job_id`, so:
- New jobs are inserted
- Existing jobs are updated with latest data
- Safe to run multiple times
- Idempotent operation

## Troubleshooting

### Missing search_keyword

If jobs scraped before the `search_keyword` field was added have `null`:
- Re-scrape those jobs with the updated scraper
- Or update the JSON files manually

### Connection Errors

Check:
- `.env` file has correct `SUPABASE_URL` and `SUPABASE_KEY`
- Network connectivity to Supabase
- API key has necessary permissions

### Data Validation Errors

Run with `--dry-run` to identify:
- Malformed JSON files
- Missing required fields
- Data type mismatches

## Schema Updates

To modify the schema:

1. Update `ns_jobs_schema.sql`
2. Create an **ALTER TABLE** migration in Supabase SQL Editor
3. Update the `transform_job_for_db()` function in `upload_to_supabase.py`
4. Test with `--dry-run`

## Best Practices

1. **Always test with --dry-run first**
2. **Backup your data** before schema changes
3. **Use service_role key** for backend operations
4. **Monitor Supabase quotas** on free tier
5. **Set up periodic re-scraping** to catch job updates
6. **Create database backups** regularly

## Support

For issues with:
- **Scraper:** Check `logs/NS/` for error messages
- **Database:** Check Supabase logs in dashboard
- **Upload script:** Run with Python debugger or add print statements
