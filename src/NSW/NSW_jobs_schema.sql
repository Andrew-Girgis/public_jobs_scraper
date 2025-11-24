-- New South Wales (Australia) Government Jobs Table Schema
-- Drop existing table if it exists
DROP TABLE IF EXISTS public.nsw_jobs CASCADE;

CREATE TABLE IF NOT EXISTS public.nsw_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    job_reference TEXT,
    job_title TEXT NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'New South Wales, Australia',
    job_board TEXT DEFAULT 'I Work for NSW',
    organization TEXT,
    url TEXT NOT NULL,
    
    -- Location
    location TEXT, -- e.g., 'Sydney Region / Sydney - Greater West'
    
    -- Employment Details
    work_type TEXT, -- e.g., 'Full-Time', 'Part-Time', 'Contract', 'Temporary'
    job_category TEXT, -- e.g., 'Projects | Business Analysis', 'Information and Communications Technology'
    
    -- Dates
    closing_date TEXT, -- e.g., "26/11/2025 - 10:00 AM"
    closing_date_parsed DATE, -- Parsed version for queries
    
    -- Salary Information
    salary_range TEXT, -- Raw salary text (e.g., "$129,464 - $142,665 + super", "Starts from $129,464 plus superannuation")
    salary_min DECIMAL(12,2),
    salary_max DECIMAL(12,2),
    salary_currency TEXT DEFAULT 'AUD',
    
    -- Job Content
    summary TEXT, -- Truncated description (first ~200 chars)
    description_html TEXT, -- Full HTML description from job page
    description_text TEXT, -- Plain text version for search
    
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
CREATE INDEX idx_nsw_jobs_job_id ON public.nsw_jobs(job_id);
CREATE INDEX idx_nsw_jobs_job_title ON public.nsw_jobs(job_title);
CREATE INDEX idx_nsw_jobs_organization ON public.nsw_jobs(organization);
CREATE INDEX idx_nsw_jobs_location ON public.nsw_jobs(location);
CREATE INDEX idx_nsw_jobs_work_type ON public.nsw_jobs(work_type);
CREATE INDEX idx_nsw_jobs_job_category ON public.nsw_jobs(job_category);
CREATE INDEX idx_nsw_jobs_closing_date_parsed ON public.nsw_jobs(closing_date_parsed);
CREATE INDEX idx_nsw_jobs_salary_min ON public.nsw_jobs(salary_min);
CREATE INDEX idx_nsw_jobs_salary_max ON public.nsw_jobs(salary_max);
CREATE INDEX idx_nsw_jobs_scraped_at ON public.nsw_jobs(scraped_at);
CREATE INDEX idx_nsw_jobs_search_keyword ON public.nsw_jobs(search_keyword);
CREATE INDEX idx_nsw_jobs_matched_keyword ON public.nsw_jobs(matched_keyword);

-- Create full-text search index for job descriptions
CREATE INDEX idx_nsw_jobs_description_text_fts ON public.nsw_jobs USING GIN(to_tsvector('english', description_text));
CREATE INDEX idx_nsw_jobs_job_title_fts ON public.nsw_jobs USING GIN(to_tsvector('english', job_title));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_nsw_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_nsw_jobs_updated_at
    BEFORE UPDATE ON public.nsw_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_nsw_jobs_updated_at();

-- Comments for documentation
COMMENT ON TABLE public.nsw_jobs IS 'New South Wales (Australia) government job postings scraped from I Work for NSW (iworkfor.nsw.gov.au)';
COMMENT ON COLUMN public.nsw_jobs.job_id IS 'Unique job ID from I Work for NSW website (URL slug)';
COMMENT ON COLUMN public.nsw_jobs.job_reference IS 'Job reference number from employer (e.g., REQ618601, req47468)';
COMMENT ON COLUMN public.nsw_jobs.work_type IS 'Employment type (e.g., Full-Time, Part-Time, Contract, Temporary)';
COMMENT ON COLUMN public.nsw_jobs.job_category IS 'Job category from NSW (e.g., Projects | Business Analysis, Information and Communications Technology | Analysts)';
COMMENT ON COLUMN public.nsw_jobs.location IS 'Job location including region (e.g., Sydney Region / Sydney - Greater West)';
COMMENT ON COLUMN public.nsw_jobs.closing_date IS 'Application closing date with time (e.g., 26/11/2025 - 10:00 AM)';
COMMENT ON COLUMN public.nsw_jobs.salary_range IS 'Salary information as provided (e.g., Starts from $129,464 plus superannuation, $127150 - $144444)';
COMMENT ON COLUMN public.nsw_jobs.description_html IS 'Full HTML description including formatting';
COMMENT ON COLUMN public.nsw_jobs.description_text IS 'Plain text version for full-text search';
COMMENT ON COLUMN public.nsw_jobs.matched_keyword IS 'Keyword that matched this job (fuzzy matching)';
COMMENT ON COLUMN public.nsw_jobs.match_score IS 'Fuzzy match score (0-100), threshold is 80';
