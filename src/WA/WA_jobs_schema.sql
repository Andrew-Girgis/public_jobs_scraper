-- Western Australia Government Jobs Table Schema
-- Drop existing table if it exists
DROP TABLE IF EXISTS public.wa_jobs CASCADE;

CREATE TABLE IF NOT EXISTS public.wa_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    position_number TEXT,
    job_title TEXT NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'Western Australia, Australia',
    job_board TEXT DEFAULT 'Jobs.WA',
    agency TEXT, -- Government department/agency
    branch TEXT, -- Department branch/division
    division_name TEXT,
    url TEXT NOT NULL,
    
    -- Location
    location TEXT, -- e.g., 'Perth', 'Baldivis', 'Rottnest Island'
    
    -- Employment Details
    job_type TEXT, -- e.g., 'Permanent - Full Time', 'Fixed Term - Part Time', 'Contract'
    classification TEXT, -- Job classification/level (e.g., 'Level 6', 'PSC Level 6', 'L6', 'ASO7')
    
    -- Dates
    posting_date TEXT, -- Posting date (raw format: "Posting date :2025-11-24")
    closing_date TEXT, -- e.g., "2025-12-08 4:00 PM"
    closing_date_parsed TIMESTAMP WITH TIME ZONE, -- Parsed version for queries
    
    -- Salary Information
    salary TEXT, -- Full salary information (e.g., "$120,475-$132,753", "Teacher, $85,610 - $124,016 per annum (pro-rata)")
    salary_min DECIMAL(12,2),
    salary_max DECIMAL(12,2),
    salary_currency TEXT DEFAULT 'AUD',
    
    -- Job Content
    description_html TEXT NOT NULL, -- Full HTML description with all formatting
    description_text TEXT NOT NULL, -- Plain text version for search
    
    -- Attachments (stored as JSONB for flexibility)
    attachments JSONB, -- Array of objects with 'name' and 'url' fields
    
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
CREATE INDEX idx_wa_jobs_job_id ON public.wa_jobs(job_id);
CREATE INDEX idx_wa_jobs_position_number ON public.wa_jobs(position_number);
CREATE INDEX idx_wa_jobs_job_title ON public.wa_jobs(job_title);
CREATE INDEX idx_wa_jobs_agency ON public.wa_jobs(agency);
CREATE INDEX idx_wa_jobs_branch ON public.wa_jobs(branch);
CREATE INDEX idx_wa_jobs_location ON public.wa_jobs(location);
CREATE INDEX idx_wa_jobs_job_type ON public.wa_jobs(job_type);
CREATE INDEX idx_wa_jobs_classification ON public.wa_jobs(classification);
CREATE INDEX idx_wa_jobs_closing_date_parsed ON public.wa_jobs(closing_date_parsed);
CREATE INDEX idx_wa_jobs_salary_min ON public.wa_jobs(salary_min);
CREATE INDEX idx_wa_jobs_salary_max ON public.wa_jobs(salary_max);
CREATE INDEX idx_wa_jobs_scraped_at ON public.wa_jobs(scraped_at);
CREATE INDEX idx_wa_jobs_search_keyword ON public.wa_jobs(search_keyword);
CREATE INDEX idx_wa_jobs_matched_keyword ON public.wa_jobs(matched_keyword);

-- Create JSONB index for attachments
CREATE INDEX idx_wa_jobs_attachments ON public.wa_jobs USING GIN(attachments);

-- Create full-text search indexes for job descriptions
CREATE INDEX idx_wa_jobs_description_text_fts ON public.wa_jobs USING GIN(to_tsvector('english', description_text));
CREATE INDEX idx_wa_jobs_job_title_fts ON public.wa_jobs USING GIN(to_tsvector('english', job_title));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_wa_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_wa_jobs_updated_at
    BEFORE UPDATE ON public.wa_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_wa_jobs_updated_at();

-- Comments for documentation
COMMENT ON TABLE public.wa_jobs IS 'Western Australia government job postings scraped from Jobs.WA (search.jobs.wa.gov.au)';
COMMENT ON COLUMN public.wa_jobs.job_id IS 'Unique job ID from Jobs.WA website (AdvertID from URL)';
COMMENT ON COLUMN public.wa_jobs.position_number IS 'Position/reference number from employer (e.g., Pool Ref 00021346, IPS/TCH1014393, 7252)';
COMMENT ON COLUMN public.wa_jobs.agency IS 'Government department or agency (e.g., Department of Health, Department of Education, GESB)';
COMMENT ON COLUMN public.wa_jobs.branch IS 'Department branch/unit (e.g., Communicable Disease Control Directorate, Baldivis Secondary College)';
COMMENT ON COLUMN public.wa_jobs.division_name IS 'Division name if different from branch';
COMMENT ON COLUMN public.wa_jobs.job_type IS 'Employment type (e.g., Permanent - Full Time, Fixed Term - Part Time, Contract)';
COMMENT ON COLUMN public.wa_jobs.classification IS 'Job classification/level (e.g., PSC Level 6, L6, Teacher, ASO7)';
COMMENT ON COLUMN public.wa_jobs.location IS 'Job location (e.g., Perth, Baldivis, Rottnest Island)';
COMMENT ON COLUMN public.wa_jobs.posting_date IS 'Job posting date as raw text (e.g., Posting date :2025-11-24)';
COMMENT ON COLUMN public.wa_jobs.closing_date IS 'Application closing date with time (e.g., 2025-12-08 4:00 PM)';
COMMENT ON COLUMN public.wa_jobs.salary IS 'Salary information as provided (e.g., $120,475-$132,753, Teacher, $85,610 - $124,016 per annum (pro-rata))';
COMMENT ON COLUMN public.wa_jobs.description_html IS 'Full HTML description including all formatting, extracted via AI';
COMMENT ON COLUMN public.wa_jobs.description_text IS 'Plain text version of description for full-text search, extracted via AI';
COMMENT ON COLUMN public.wa_jobs.attachments IS 'Array of attachment objects with name and url fields (JSONB format)';
COMMENT ON COLUMN public.wa_jobs.matched_keyword IS 'Keyword that matched this job (fuzzy matching)';
COMMENT ON COLUMN public.wa_jobs.match_score IS 'Fuzzy match score (0-100), threshold is 80';
COMMENT ON COLUMN public.wa_jobs.scraper_version IS 'Version of the scraper used (AI-powered extraction)';

-- Example attachment structure:
-- [
--   {"name": "Applicant Information Package.pdf", "url": "https://doh.bigredsky.com/files/vacancies/710409/50749810.pdf"},
--   {"name": "Job Description.pdf", "url": "https://example.com/job.pdf"}
-- ]
