-- Tasmania (Australia) Government Jobs Table Schema
-- Drop existing table if it exists
DROP TABLE IF EXISTS public.tas_jobs CASCADE;

CREATE TABLE IF NOT EXISTS public.tas_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    job_reference TEXT, -- Optional job reference number
    job_title TEXT NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'Tasmania, Australia',
    job_board TEXT DEFAULT 'Jobs Tasmania',
    agency TEXT NOT NULL, -- Tasmanian government agency/department
    url TEXT NOT NULL,
    
    -- Location
    region TEXT, -- South, North, North West, Statewide
    location TEXT, -- Specific city/town
    
    -- Employment Details
    employment_type TEXT, -- e.g., 'Permanent, full-time', 'Fixed-term, flexible'
    award TEXT, -- e.g., 'Tasmanian State Service Award - General Stream Band 3'
    
    -- Dates
    closing_date TEXT, -- Store as TEXT since format varies (e.g., "Monday 25 January, 2027 5:00 PM")
    closing_date_parsed TIMESTAMP WITH TIME ZONE, -- Parsed version for queries
    
    -- Salary Information
    salary TEXT, -- Raw salary text (e.g., "$74,783.00 to $80,835.00 per annum", "$99,482.00 to $104,352.00 per annum")
    salary_min DECIMAL(12,2),
    salary_max DECIMAL(12,2),
    salary_currency TEXT DEFAULT 'AUD',
    
    -- Job Content
    summary TEXT, -- Job description from search results
    description_html TEXT, -- Full HTML description from job page
    description_text TEXT, -- Plain text version for search (extracted from HTML)
    
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
CREATE INDEX idx_tas_jobs_job_id ON public.tas_jobs(job_id);
CREATE INDEX idx_tas_jobs_job_title ON public.tas_jobs(job_title);
CREATE INDEX idx_tas_jobs_agency ON public.tas_jobs(agency);
CREATE INDEX idx_tas_jobs_region ON public.tas_jobs(region);
CREATE INDEX idx_tas_jobs_location ON public.tas_jobs(location);
CREATE INDEX idx_tas_jobs_employment_type ON public.tas_jobs(employment_type);
CREATE INDEX idx_tas_jobs_award ON public.tas_jobs(award);
CREATE INDEX idx_tas_jobs_closing_date_parsed ON public.tas_jobs(closing_date_parsed);
CREATE INDEX idx_tas_jobs_salary_min ON public.tas_jobs(salary_min);
CREATE INDEX idx_tas_jobs_salary_max ON public.tas_jobs(salary_max);
CREATE INDEX idx_tas_jobs_scraped_at ON public.tas_jobs(scraped_at);
CREATE INDEX idx_tas_jobs_search_keyword ON public.tas_jobs(search_keyword);
CREATE INDEX idx_tas_jobs_matched_keyword ON public.tas_jobs(matched_keyword);

-- Create full-text search index for job descriptions
CREATE INDEX idx_tas_jobs_description_text_fts ON public.tas_jobs USING GIN(to_tsvector('english', description_text));
CREATE INDEX idx_tas_jobs_job_title_fts ON public.tas_jobs USING GIN(to_tsvector('english', job_title));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_tas_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tas_jobs_updated_at
    BEFORE UPDATE ON public.tas_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_tas_jobs_updated_at();

-- Comments for documentation
COMMENT ON TABLE public.tas_jobs IS 'Tasmania (Australia) government job postings scraped from Jobs Tasmania (careers.pageuppeople.com)';
COMMENT ON COLUMN public.tas_jobs.job_id IS 'Unique job ID from Jobs Tasmania website';
COMMENT ON COLUMN public.tas_jobs.job_reference IS 'Optional job reference number from employer';
COMMENT ON COLUMN public.tas_jobs.agency IS 'Tasmanian government agency or department (e.g., Department of Police, Fire and Emergency Management)';
COMMENT ON COLUMN public.tas_jobs.region IS 'Geographic region in Tasmania (South, North, North West, Statewide)';
COMMENT ON COLUMN public.tas_jobs.location IS 'Specific city or town location';
COMMENT ON COLUMN public.tas_jobs.employment_type IS 'Type of employment (e.g., Permanent, full-time; Fixed-term, flexible)';
COMMENT ON COLUMN public.tas_jobs.award IS 'Award classification (e.g., Tasmanian State Service Award - General Stream Band 3)';
COMMENT ON COLUMN public.tas_jobs.closing_date IS 'Original closing date string from website';
COMMENT ON COLUMN public.tas_jobs.closing_date_parsed IS 'Parsed closing date as timestamp for queries';
COMMENT ON COLUMN public.tas_jobs.salary IS 'Original salary string (e.g., "$74,783.00 to $80,835.00 per annum")';
COMMENT ON COLUMN public.tas_jobs.salary_min IS 'Minimum salary extracted from salary string';
COMMENT ON COLUMN public.tas_jobs.salary_max IS 'Maximum salary extracted from salary string';
COMMENT ON COLUMN public.tas_jobs.summary IS 'Brief job description from search results';
COMMENT ON COLUMN public.tas_jobs.description_html IS 'Full HTML job description from detail page';
COMMENT ON COLUMN public.tas_jobs.description_text IS 'Plain text version of description for full-text search';
COMMENT ON COLUMN public.tas_jobs.search_keyword IS 'Original search keyword that found this job';
COMMENT ON COLUMN public.tas_jobs.matched_keyword IS 'The keyword that matched via fuzzy matching';
COMMENT ON COLUMN public.tas_jobs.match_score IS 'Fuzzy match score (0-100)';
