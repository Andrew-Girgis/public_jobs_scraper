-- Queensland (Australia) Government Jobs Table Schema
-- Drop existing table if it exists
DROP TABLE IF EXISTS public.qld_jobs CASCADE;

CREATE TABLE IF NOT EXISTS public.qld_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    job_reference TEXT, -- e.g., "QLD/667984"
    job_title TEXT NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'Queensland, Australia',
    job_board TEXT DEFAULT 'SmartJobs Queensland',
    organization TEXT, -- e.g., "Queensland Health", "Crime and Corruption Commission"
    department TEXT, -- Sub-department if applicable
    url TEXT NOT NULL,
    
    -- Location
    location TEXT, -- e.g., "Brisbane Inner City", "Mackay region", "Wide Bay"
    
    -- Employment Details
    position_status TEXT, -- e.g., "Permanent", "Contract", "Fixed Term Temporary", "Casual"
    position_type TEXT, -- e.g., "Full-time", "Flexible full-time", "Part-time", "Flexible-part-time"
    occupational_group TEXT, -- e.g., "Administration", "IT & Telecommunications", "Health - Nursing"
    classification TEXT, -- e.g., "AO7", "AO6", "Nurse Grade 6 (1)", "PO6"
    
    -- Dates
    closing_date TEXT, -- Store as TEXT (e.g., "26-Nov-2025", "18-Nov-2025")
    closing_date_parsed DATE, -- Parsed version for queries
    date_posted TEXT, -- If available from job page
    date_posted_parsed DATE,
    
    -- Salary Information (Queensland has 3 types)
    salary_yearly TEXT, -- e.g., "$119802 - $127942 (yearly)"
    salary_fortnightly TEXT, -- e.g., "$4592.00 - $4904.00 (fortnightly)"
    total_remuneration TEXT, -- e.g., "$136889 up to $146190 (total remuneration)"
    salary_min DECIMAL(12,2), -- Extracted from yearly or fortnightly
    salary_max DECIMAL(12,2),
    salary_currency TEXT DEFAULT 'AUD',
    
    -- Job Content
    summary TEXT, -- Job description from search results (plain text)
    description_html TEXT, -- Full HTML description from job page
    description_text TEXT, -- Plain text version for search (extracted from HTML)
    
    -- Contact Information
    contact_person TEXT, -- e.g., "Diana Bui Byrne"
    contact_details TEXT, -- e.g., "0408 366 279  Access the National Relay Service"
    
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
CREATE INDEX idx_qld_jobs_job_id ON public.qld_jobs(job_id);
CREATE INDEX idx_qld_jobs_job_title ON public.qld_jobs(job_title);
CREATE INDEX idx_qld_jobs_organization ON public.qld_jobs(organization);
CREATE INDEX idx_qld_jobs_department ON public.qld_jobs(department);
CREATE INDEX idx_qld_jobs_location ON public.qld_jobs(location);
CREATE INDEX idx_qld_jobs_position_status ON public.qld_jobs(position_status);
CREATE INDEX idx_qld_jobs_position_type ON public.qld_jobs(position_type);
CREATE INDEX idx_qld_jobs_occupational_group ON public.qld_jobs(occupational_group);
CREATE INDEX idx_qld_jobs_classification ON public.qld_jobs(classification);
CREATE INDEX idx_qld_jobs_closing_date_parsed ON public.qld_jobs(closing_date_parsed);
CREATE INDEX idx_qld_jobs_date_posted_parsed ON public.qld_jobs(date_posted_parsed);
CREATE INDEX idx_qld_jobs_salary_min ON public.qld_jobs(salary_min);
CREATE INDEX idx_qld_jobs_salary_max ON public.qld_jobs(salary_max);
CREATE INDEX idx_qld_jobs_scraped_at ON public.qld_jobs(scraped_at);
CREATE INDEX idx_qld_jobs_search_keyword ON public.qld_jobs(search_keyword);
CREATE INDEX idx_qld_jobs_matched_keyword ON public.qld_jobs(matched_keyword);

-- Create full-text search index for job descriptions
CREATE INDEX idx_qld_jobs_description_text_fts ON public.qld_jobs USING GIN(to_tsvector('english', description_text));
CREATE INDEX idx_qld_jobs_job_title_fts ON public.qld_jobs USING GIN(to_tsvector('english', job_title));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_qld_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_qld_jobs_updated_at
    BEFORE UPDATE ON public.qld_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_qld_jobs_updated_at();

-- Comments for documentation
COMMENT ON TABLE public.qld_jobs IS 'Queensland (Australia) government job postings scraped from SmartJobs Queensland';
COMMENT ON COLUMN public.qld_jobs.job_id IS 'Unique job ID from SmartJobs (e.g., "223089947" or "QLD-667984-25")';
COMMENT ON COLUMN public.qld_jobs.job_reference IS 'Job reference number (e.g., "QLD/667984", "QLD/HPSP669410")';
COMMENT ON COLUMN public.qld_jobs.organization IS 'Queensland government organization (e.g., "Queensland Health", "Queensland Police Service")';
COMMENT ON COLUMN public.qld_jobs.department IS 'Sub-department or division if applicable';
COMMENT ON COLUMN public.qld_jobs.location IS 'Geographic location (e.g., "Brisbane Inner City", "Mackay region", "Cairns region")';
COMMENT ON COLUMN public.qld_jobs.position_status IS 'Employment status (Permanent, Contract, Fixed Term Temporary, Casual)';
COMMENT ON COLUMN public.qld_jobs.position_type IS 'Work arrangement (Full-time, Flexible full-time, Part-time, Flexible-part-time)';
COMMENT ON COLUMN public.qld_jobs.occupational_group IS 'Job category (e.g., "Administration", "IT & Telecommunications", "Health - Nursing")';
COMMENT ON COLUMN public.qld_jobs.classification IS 'Queensland classification level (e.g., "AO7", "AO6", "Nurse Grade 6 (1)", "PO6")';
COMMENT ON COLUMN public.qld_jobs.closing_date IS 'Original closing date string from website (e.g., "26-Nov-2025")';
COMMENT ON COLUMN public.qld_jobs.closing_date_parsed IS 'Parsed closing date for queries';
COMMENT ON COLUMN public.qld_jobs.salary_yearly IS 'Yearly salary range (e.g., "$119802 - $127942 (yearly)")';
COMMENT ON COLUMN public.qld_jobs.salary_fortnightly IS 'Fortnightly salary range (e.g., "$4592.00 - $4904.00 (fortnightly)")';
COMMENT ON COLUMN public.qld_jobs.total_remuneration IS 'Total remuneration package (e.g., "$136889 up to $146190 (total remuneration)")';
COMMENT ON COLUMN public.qld_jobs.salary_min IS 'Minimum salary extracted from yearly or fortnightly';
COMMENT ON COLUMN public.qld_jobs.salary_max IS 'Maximum salary extracted from yearly or fortnightly';
COMMENT ON COLUMN public.qld_jobs.summary IS 'Brief job description from search results (plain text)';
COMMENT ON COLUMN public.qld_jobs.description_html IS 'Full HTML job description from detail page';
COMMENT ON COLUMN public.qld_jobs.description_text IS 'Plain text version of description for full-text search';
COMMENT ON COLUMN public.qld_jobs.contact_person IS 'Contact person name';
COMMENT ON COLUMN public.qld_jobs.contact_details IS 'Contact details (phone, email, relay service info)';
COMMENT ON COLUMN public.qld_jobs.search_keyword IS 'Original search keyword that found this job';
COMMENT ON COLUMN public.qld_jobs.matched_keyword IS 'The keyword that matched via fuzzy matching';
COMMENT ON COLUMN public.qld_jobs.match_score IS 'Fuzzy match score (0-100)';
