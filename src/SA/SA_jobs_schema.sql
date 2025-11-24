-- South Australia Government Jobs Table Schema
-- Drop existing table if it exists
DROP TABLE IF EXISTS public.sa_jobs CASCADE;

CREATE TABLE IF NOT EXISTS public.sa_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    reference_number TEXT,
    job_title TEXT NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'South Australia, Australia',
    job_board TEXT DEFAULT 'I Work for SA',
    agency TEXT,
    url TEXT NOT NULL,
    
    -- Location
    location TEXT, -- e.g., '5000 - ADELAIDE'
    
    -- Employment Details
    job_status TEXT, -- e.g., 'Long Term Contract', 'Ongoing', 'Temporary'
    eligibility TEXT, -- e.g., 'Open to Everyone'
    
    -- Dates
    posting_date TEXT, -- e.g., "14/11/2025"
    posting_date_parsed DATE, -- Parsed version for queries
    closing_date TEXT, -- e.g., "28/11/2025 5:00 PM"
    closing_date_parsed DATE, -- Parsed version for queries
    
    -- Salary Information (raw text for AI extraction)
    salary TEXT, -- Raw salary text (e.g., "ASO7 - $108,109 - $116,864 per annum", "MAS3 $127,859 p.a. plus superannuation")
    salary_min DECIMAL(12,2), -- Extracted minimum salary
    salary_max DECIMAL(12,2), -- Extracted maximum salary
    salary_currency TEXT DEFAULT 'AUD',
    
    -- Job Content
    description_html TEXT, -- Full HTML description from job page
    description_text TEXT, -- Plain text version for search
    
    -- Attachments (stored as JSONB array)
    attachments JSONB, -- Array of {name: string, url: string}
    
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
CREATE INDEX idx_sa_jobs_job_id ON public.sa_jobs(job_id);
CREATE INDEX idx_sa_jobs_job_title ON public.sa_jobs(job_title);
CREATE INDEX idx_sa_jobs_reference_number ON public.sa_jobs(reference_number);
CREATE INDEX idx_sa_jobs_agency ON public.sa_jobs(agency);
CREATE INDEX idx_sa_jobs_location ON public.sa_jobs(location);
CREATE INDEX idx_sa_jobs_job_status ON public.sa_jobs(job_status);
CREATE INDEX idx_sa_jobs_eligibility ON public.sa_jobs(eligibility);
CREATE INDEX idx_sa_jobs_posting_date_parsed ON public.sa_jobs(posting_date_parsed);
CREATE INDEX idx_sa_jobs_closing_date_parsed ON public.sa_jobs(closing_date_parsed);
CREATE INDEX idx_sa_jobs_salary_min ON public.sa_jobs(salary_min);
CREATE INDEX idx_sa_jobs_salary_max ON public.sa_jobs(salary_max);
CREATE INDEX idx_sa_jobs_scraped_at ON public.sa_jobs(scraped_at);
CREATE INDEX idx_sa_jobs_search_keyword ON public.sa_jobs(search_keyword);
CREATE INDEX idx_sa_jobs_matched_keyword ON public.sa_jobs(matched_keyword);

-- Create GIN index for JSONB attachments
CREATE INDEX idx_sa_jobs_attachments ON public.sa_jobs USING GIN(attachments);

-- Create full-text search indexes
CREATE INDEX idx_sa_jobs_description_text_fts ON public.sa_jobs USING GIN(to_tsvector('english', description_text));
CREATE INDEX idx_sa_jobs_job_title_fts ON public.sa_jobs USING GIN(to_tsvector('english', job_title));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_sa_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_sa_jobs_updated_at
    BEFORE UPDATE ON public.sa_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_sa_jobs_updated_at();

-- Comments for documentation
COMMENT ON TABLE public.sa_jobs IS 'South Australia government job postings scraped from I Work for SA (iworkfor.sa.gov.au)';
COMMENT ON COLUMN public.sa_jobs.job_id IS 'Unique job ID from I Work for SA website (AdvertID from URL)';
COMMENT ON COLUMN public.sa_jobs.reference_number IS 'Job reference number from employer (e.g., 708751, 709121)';
COMMENT ON COLUMN public.sa_jobs.agency IS 'Government agency posting the job (e.g., South Australia Police, Department of State Development)';
COMMENT ON COLUMN public.sa_jobs.location IS 'Job location with postcode (e.g., 5000 - ADELAIDE)';
COMMENT ON COLUMN public.sa_jobs.job_status IS 'Employment type (e.g., Long Term Contract, Ongoing, Temporary)';
COMMENT ON COLUMN public.sa_jobs.eligibility IS 'Eligibility requirements (e.g., Open to Everyone)';
COMMENT ON COLUMN public.sa_jobs.posting_date IS 'Date job was posted in DD/MM/YYYY format';
COMMENT ON COLUMN public.sa_jobs.closing_date IS 'Application closing date with time (e.g., 28/11/2025 5:00 PM)';
COMMENT ON COLUMN public.sa_jobs.salary IS 'Raw salary information as provided (inconsistent format - use AI for extraction)';
COMMENT ON COLUMN public.sa_jobs.salary_min IS 'Extracted minimum salary (to be populated via AI or manual parsing)';
COMMENT ON COLUMN public.sa_jobs.salary_max IS 'Extracted maximum salary (to be populated via AI or manual parsing)';
COMMENT ON COLUMN public.sa_jobs.description_html IS 'Full HTML description including formatting';
COMMENT ON COLUMN public.sa_jobs.description_text IS 'Plain text version for full-text search';
COMMENT ON COLUMN public.sa_jobs.attachments IS 'JSONB array of attachment objects with name and url fields';
COMMENT ON COLUMN public.sa_jobs.matched_keyword IS 'Keyword that matched this job (fuzzy matching)';
COMMENT ON COLUMN public.sa_jobs.match_score IS 'Fuzzy match score (0-100), threshold is 80';
