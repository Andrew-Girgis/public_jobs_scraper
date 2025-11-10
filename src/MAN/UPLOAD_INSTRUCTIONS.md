# How to Upload Nova Scotia Jobs to Supabase

## ✅ Prerequisites (Already Complete!)

- ✓ Supabase Python package installed
- ✓ `.env` file configured with `SUPABASE_URL` and `SUPABASE_KEY`
- ✓ 14 NS job files validated and ready to upload
- ✓ Upload script tested with dry-run

## Step 1: Create the Database Table

Before uploading jobs, you need to create the `ns_jobs` table in Supabase:

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Click **SQL Editor** in the left sidebar
4. Click **New Query**
5. Copy the entire contents of `/database/ns_jobs_schema.sql`
6. Paste into the SQL Editor
7. Click **Run** (or press Cmd+Enter)

You should see: ✅ Success. No rows returned

## Step 2: Upload Jobs

Once the table is created, run the upload script:

```bash
# From the project root directory
python -m src.NS.upload_to_supabase
```

### Expected Output:

```
================================================================================
Nova Scotia Jobs Uploader
================================================================================
Found 14 job files

📤 Uploading to Supabase...
✓ Uploaded job 596949917: Provincial Coordination Centre Watch Supervisor
✓ Uploaded job 596820517: Executive Director, Tax, Economics and Fiscal Policy
✓ Uploaded job 597021517: Program Administration Officer 3
✓ Uploaded job 597038917: Cyber Security Risk Advisor
✓ Uploaded job 597132717: Manager, Project Manager
✓ Uploaded job 597025017: Manager, Building Infrastructure
✓ Uploaded job 597112117: Category Manager (Manager, Strategic Sourcing)
✓ Uploaded job 597235617: Senior Policy Analyst
✓ Uploaded job 597113117: Procurement Specialist
✓ Uploaded job 597212417: Manager, Investigations and Compliance
✓ Uploaded job 596968317: Senior Cyber and Risk Analyst
✓ Uploaded job 597063717: Project Coordinator Intern
✓ Uploaded job 596991817: Manager, Talent Acquisition
✓ Uploaded job 597220517: Manager, Financial Advisory Services

================================================================================
Upload Complete
================================================================================
✓ Successfully uploaded: 14
✗ Failed: 0
📊 Total: 14
================================================================================
```

## Step 3: Verify in Supabase

1. Go to **Table Editor** in Supabase Dashboard
2. Select the `ns_jobs` table
3. You should see 14 rows with all your job data

## Troubleshooting

### Error: "Table 'ns_jobs' does not exist"
**Solution:** Run the SQL schema from Step 1 first

### Error: "Invalid API key"
**Solution:** Check your `.env` file has the correct `SUPABASE_KEY` (use service_role key)

### Error: "Column does not exist"
**Solution:** Make sure you ran the complete schema SQL, not just part of it

### Some jobs failed to upload
**Solution:** Check the error message for the specific job and verify the JSON format

## Re-running the Upload

The script uses **UPSERT** on `job_id`, so it's safe to run multiple times:
- New jobs will be inserted
- Existing jobs will be updated with latest data
- No duplicates will be created

To re-upload all jobs:
```bash
python -m src.NS.upload_to_supabase
```

## Commands Reference

### Validate without uploading (Dry run)
```bash
python -m src.NS.upload_to_supabase --dry-run
```

### Upload all jobs
```bash
python -m src.NS.upload_to_supabase
```

### Check upload script help
```bash
python -m src.NS.upload_to_supabase --help
```

## What Gets Uploaded

Each job includes:
- ✓ Job metadata (title, department, location, dates)
- ✓ Compensation (salary range, pay grade)
- ✓ All content sections (about us, qualifications, benefits, etc.)
- ✓ Arrays (bullets) as JSONB
- ✓ Scraping metadata (search_keyword, matched_keyword, match_score)
- ✓ Timestamps (scraped_at, created_at, updated_at)

## Next Steps After Upload

### Query your data in Supabase SQL Editor:

**View all jobs:**
```sql
SELECT job_id, job_title, department, closing_date
FROM ns_jobs
ORDER BY scraped_at DESC;
```

**Search by keyword:**
```sql
SELECT job_title, matched_keyword, match_score
FROM ns_jobs
WHERE matched_keyword = 'Manager'
ORDER BY match_score DESC;
```

**Jobs closing soon:**
```sql
SELECT job_title, department, closing_date
FROM ns_jobs
WHERE closing_date > NOW()
ORDER BY closing_date
LIMIT 10;
```

**Salary analysis:**
```sql
SELECT 
    department,
    COUNT(*) as jobs,
    AVG(salary_max) as avg_max_salary
FROM ns_jobs
WHERE salary_max IS NOT NULL
GROUP BY department
ORDER BY avg_max_salary DESC;
```

## Automated Updates

To keep your database updated:

1. Run the NS scraper regularly:
   ```bash
   python -m src.NS.ns_scraper
   ```

2. Then upload new/updated jobs:
   ```bash
   python -m src.NS.upload_to_supabase
   ```

The script will automatically:
- Insert new jobs
- Update changed jobs (by job_id)
- Skip unchanged jobs

You can set up a cron job or scheduled task to run both commands daily/weekly.
