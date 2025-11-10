# Uploading GOC Jobs to Supabase

## Prerequisites

1. **Supabase Project**: Create a project at [supabase.com](https://supabase.com)
2. **Database Schema**: Run the `src/GOC/goc_jobs_schema.sql` file in your Supabase SQL Editor
3. **Python Package**: Install the Supabase client (already done if you see this)

## Setup

### 1. Get Your Supabase Credentials

From your Supabase project dashboard:
1. Go to **Settings** → **API**
2. Copy your **Project URL** (looks like `https://xxxxx.supabase.co`)
3. Copy your **service_role key** (for server-side uploads) or **anon key** (for testing)

### 2. Set Environment Variables

**Option A: Set in your current terminal session**
```bash
export SUPABASE_URL='https://your-project-id.supabase.co'
export SUPABASE_KEY='your-service-role-key-here'
```

**Option B: Create a `.env` file** (recommended)
```bash
# Create .env file in project root
cat > .env << 'EOF'
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-service-role-key-here
EOF

# Load the environment variables
source .env
```

**Option C: Add to your shell profile** (permanent)
```bash
# Add to ~/.zshrc or ~/.bashrc
echo 'export SUPABASE_URL="https://your-project-id.supabase.co"' >> ~/.zshrc
echo 'export SUPABASE_KEY="your-service-role-key-here"' >> ~/.zshrc
source ~/.zshrc
```

## Usage

### Dry Run (Validate Files First)
Test that all JSON files are valid without uploading:
```bash
python src/GOC/upload_to_supabase.py --dry-run
```

### Upload a Few Jobs (Testing)
Upload just the first 10 jobs to test:
```bash
python src/GOC/upload_to_supabase.py --limit 10
```

### Upload All Jobs
Upload all scraped jobs to Supabase:
```bash
python src/GOC/upload_to_supabase.py
```

## What It Does

The uploader:
- ✅ Reads all JSON files from `data/GOC/jobs_json/`
- ✅ Connects to your Supabase database
- ✅ **Upserts** each job (inserts new or updates existing based on `poster_id`)
- ✅ Shows progress for each job
- ✅ Provides a summary at the end

## Verifying the Upload

After uploading, you can verify in Supabase:

1. **In the Supabase Dashboard:**
   - Go to **Table Editor** → `goc_jobs`
   - You should see all your uploaded jobs

2. **Run a SQL Query:**
```sql
-- Count jobs by structure type
SELECT structure_type, COUNT(*) as count
FROM goc_jobs
GROUP BY structure_type;

-- See recent uploads
SELECT poster_id, title, department, scraped_at
FROM goc_jobs
ORDER BY scraped_at DESC
LIMIT 10;
```

## Troubleshooting

### "Supabase credentials not found"
Make sure you've set the environment variables:
```bash
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

### "relation 'goc_jobs' does not exist"
Run the SQL schema file first:
1. Open Supabase Dashboard → SQL Editor
2. Copy contents of `src/GOC/goc_jobs_schema.sql`
3. Run the query

### Permission Errors
Make sure you're using the **service_role** key (not anon key) for uploads, as it has full access.

## Next Steps

After uploading:
1. Query your data in Supabase
2. Set up Row Level Security (RLS) policies if needed
3. Create views for common queries
4. Build a frontend to display the jobs!
