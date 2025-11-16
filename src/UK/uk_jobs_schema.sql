-- United Kingdom Government Jobs Table Schema
-- Drop existing table if it exists
DROP TABLE IF EXISTS public.uk_jobs CASCADE;

CREATE TABLE IF NOT EXISTS public.uk_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    job_reference TEXT,
    job_title TEXT NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'United Kingdom',
    job_board TEXT DEFAULT 'Find a Job (DWP)',
    company TEXT,
    url TEXT NOT NULL,
    
    -- Location and Work Arrangement
    location TEXT,
    remote_working TEXT, -- null, 'Hybrid', 'Remote', 'On-site'
    
    -- Employment Details
    hours TEXT, -- e.g., 'Full time', 'Part time'
    job_type TEXT, -- e.g., 'Permanent', 'Contract', 'Temporary'
    
    -- Dates
    posting_date TEXT, -- Store as TEXT since format varies (e.g., "27 June 2025")
    closing_date TEXT,
    posting_date_parsed DATE, -- Parsed version for queries
    closing_date_parsed DATE,
    
    -- Salary Information
    salary TEXT, -- Raw salary text (e.g., "£30,000 - £40,000", "Not specified")
    salary_min DECIMAL(12,2),
    salary_max DECIMAL(12,2),
    salary_currency TEXT DEFAULT 'GBP',
    salary_frequency TEXT, -- 'per annum', 'per hour', etc.
    
    -- Job Content
    summary TEXT, -- First 500 chars of description
    description_html TEXT, -- Full HTML description from job page
    description_text TEXT, -- Plain text version for search
    
    -- Tags/Categories
    tags JSONB, -- Array of tag strings (e.g., ['On-site', 'Permanent'])
    
    -- Scraping Metadata
    search_keyword TEXT NOT NULL,
    matched_keyword TEXT,
    match_score INTEGER,
    scraped_at TIMESTAMP WITH TIME ZONE,
    scraper_version TEXT DEFAULT '1.0',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_uk_jobs_job_id ON public.uk_jobs(job_id);
CREATE INDEX idx_uk_jobs_job_title ON public.uk_jobs(job_title);
CREATE INDEX idx_uk_jobs_company ON public.uk_jobs(company);
CREATE INDEX idx_uk_jobs_location ON public.uk_jobs(location);
CREATE INDEX idx_uk_jobs_job_type ON public.uk_jobs(job_type);
CREATE INDEX idx_uk_jobs_hours ON public.uk_jobs(hours);
CREATE INDEX idx_uk_jobs_closing_date_parsed ON public.uk_jobs(closing_date_parsed);
CREATE INDEX idx_uk_jobs_posting_date_parsed ON public.uk_jobs(posting_date_parsed);
CREATE INDEX idx_uk_jobs_salary_min ON public.uk_jobs(salary_min);
CREATE INDEX idx_uk_jobs_salary_max ON public.uk_jobs(salary_max);
CREATE INDEX idx_uk_jobs_scraped_at ON public.uk_jobs(scraped_at);
CREATE INDEX idx_uk_jobs_search_keyword ON public.uk_jobs(search_keyword);
CREATE INDEX idx_uk_jobs_matched_keyword ON public.uk_jobs(matched_keyword);
CREATE INDEX idx_uk_jobs_remote_working ON public.uk_jobs(remote_working);

-- Create full-text search index for job descriptions
CREATE INDEX idx_uk_jobs_description_text_fts ON public.uk_jobs USING GIN(to_tsvector('english', description_text));
CREATE INDEX idx_uk_jobs_job_title_fts ON public.uk_jobs USING GIN(to_tsvector('english', job_title));

-- Create JSONB index for tags
CREATE INDEX idx_uk_jobs_tags ON public.uk_jobs USING GIN(tags);

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_uk_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_uk_jobs_updated_at
    BEFORE UPDATE ON public.uk_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_uk_jobs_updated_at();

-- Comments for documentation
COMMENT ON TABLE public.uk_jobs IS 'UK government and public sector job postings scraped from Find a Job (DWP)';
COMMENT ON COLUMN public.uk_jobs.job_id IS 'Unique job ID from Find a Job website';
COMMENT ON COLUMN public.uk_jobs.job_reference IS 'Job reference number from employer';
COMMENT ON COLUMN public.uk_jobs.description_html IS 'Full HTML description including formatting';
COMMENT ON COLUMN public.uk_jobs.description_text IS 'Plain text version for full-text search';
COMMENT ON COLUMN public.uk_jobs.tags IS 'Array of tags like ["On-site", "Permanent"]';
COMMENT ON COLUMN public.uk_jobs.matched_keyword IS 'Keyword that matched this job (fuzzy matching)';
COMMENT ON COLUMN public.uk_jobs.match_score IS 'Fuzzy match score (0-100), threshold is 80';
COMMENT ON COLUMN public.uk_jobs.remote_working IS 'Remote work status: null, Hybrid, Remote, or On-site';
