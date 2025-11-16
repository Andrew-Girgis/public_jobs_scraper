-- Victoria (Australia) Government Jobs Table Schema
-- Drop existing table if it exists
DROP TABLE IF EXISTS public.vic_jobs CASCADE;

CREATE TABLE IF NOT EXISTS public.vic_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    job_reference TEXT,
    job_title TEXT NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'Victoria, Australia',
    job_board TEXT DEFAULT 'Careers Victoria',
    organization TEXT,
    url TEXT NOT NULL,
    
    -- Location
    location TEXT,
    
    -- Employment Details
    work_type TEXT, -- e.g., 'Ongoing - Full-time', 'Fixed-term - Full-time'
    grade TEXT, -- VPS grade (e.g., 'VPS 3', 'VPS 4', 'VPS 6')
    occupation TEXT, -- e.g., 'IT and telecommunications', 'Human resources', 'Consulting and strategy'
    
    -- Dates
    posted_date TEXT, -- Store as TEXT since format varies (e.g., "31 October 2025")
    closing_date TEXT, -- e.g., "Monday 17 November 2025"
    posted_date_parsed DATE, -- Parsed version for queries
    closing_date_parsed DATE,
    
    -- Salary Information
    salary TEXT, -- Raw salary text (e.g., "$79,122 - $96,073", "$138,631 - $185,518")
    salary_min DECIMAL(12,2),
    salary_max DECIMAL(12,2),
    salary_currency TEXT DEFAULT 'AUD',
    
    -- Job Content
    summary TEXT, -- First 500 chars of description
    description_html TEXT, -- Full HTML description from job page
    description_text TEXT, -- Plain text version for search
    
    -- Additional Information
    logo_url TEXT, -- Organization logo URL
    
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
CREATE INDEX idx_vic_jobs_job_id ON public.vic_jobs(job_id);
CREATE INDEX idx_vic_jobs_job_title ON public.vic_jobs(job_title);
CREATE INDEX idx_vic_jobs_organization ON public.vic_jobs(organization);
CREATE INDEX idx_vic_jobs_location ON public.vic_jobs(location);
CREATE INDEX idx_vic_jobs_work_type ON public.vic_jobs(work_type);
CREATE INDEX idx_vic_jobs_grade ON public.vic_jobs(grade);
CREATE INDEX idx_vic_jobs_occupation ON public.vic_jobs(occupation);
CREATE INDEX idx_vic_jobs_closing_date_parsed ON public.vic_jobs(closing_date_parsed);
CREATE INDEX idx_vic_jobs_posted_date_parsed ON public.vic_jobs(posted_date_parsed);
CREATE INDEX idx_vic_jobs_salary_min ON public.vic_jobs(salary_min);
CREATE INDEX idx_vic_jobs_salary_max ON public.vic_jobs(salary_max);
CREATE INDEX idx_vic_jobs_scraped_at ON public.vic_jobs(scraped_at);
CREATE INDEX idx_vic_jobs_search_keyword ON public.vic_jobs(search_keyword);
CREATE INDEX idx_vic_jobs_matched_keyword ON public.vic_jobs(matched_keyword);

-- Create full-text search index for job descriptions
CREATE INDEX idx_vic_jobs_description_text_fts ON public.vic_jobs USING GIN(to_tsvector('english', description_text));
CREATE INDEX idx_vic_jobs_job_title_fts ON public.vic_jobs USING GIN(to_tsvector('english', job_title));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_vic_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_vic_jobs_updated_at
    BEFORE UPDATE ON public.vic_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_vic_jobs_updated_at();

-- Comments for documentation
COMMENT ON TABLE public.vic_jobs IS 'Victoria (Australia) government job postings scraped from Careers Victoria';
COMMENT ON COLUMN public.vic_jobs.job_id IS 'Unique job ID from Careers Victoria website';
COMMENT ON COLUMN public.vic_jobs.job_reference IS 'Job reference number from employer (e.g., VG/082612)';
COMMENT ON COLUMN public.vic_jobs.work_type IS 'Employment type (e.g., Ongoing - Full-time, Fixed-term - Full-time)';
COMMENT ON COLUMN public.vic_jobs.grade IS 'Victorian Public Service (VPS) grade level (e.g., VPS 3, VPS 4)';
COMMENT ON COLUMN public.vic_jobs.occupation IS 'Job occupation category (e.g., IT and telecommunications, Human resources)';
COMMENT ON COLUMN public.vic_jobs.description_html IS 'Full HTML description including formatting';
COMMENT ON COLUMN public.vic_jobs.description_text IS 'Plain text version for full-text search';
COMMENT ON COLUMN public.vic_jobs.matched_keyword IS 'Keyword that matched this job (fuzzy matching)';
COMMENT ON COLUMN public.vic_jobs.match_score IS 'Fuzzy match score (0-100), threshold is 80';
COMMENT ON COLUMN public.vic_jobs.logo_url IS 'URL to organization logo image';
