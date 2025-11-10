-- Manitoba Government Jobs Table Schema
-- Drop existing table if it exists
CREATE TABLE IF NOT EXISTS public.man_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    job_title TEXT NOT NULL,
    advertisement_number TEXT,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'Manitoba',
    job_board TEXT DEFAULT 'Government of Manitoba Careers',
    url TEXT NOT NULL,
    
    -- Employment Details
    classification_title TEXT,
    classification_code TEXT,
    employment_types JSONB, -- Array of employment types (e.g., ["Regular/full-time"])
    departments JSONB, -- Array of departments
    divisions JSONB, -- Array of divisions
    locations JSONB, -- Array of locations
    
    -- Salary Information
    salary_raw_text TEXT,
    salary_classification_code TEXT,
    salary_min DECIMAL(12,2),
    salary_max DECIMAL(12,2),
    salary_frequency TEXT, -- 'per year', 'per hour', etc.
    salary_currency TEXT DEFAULT 'CAD',
    
    -- Dates
    closing_date DATE,
    closing_time TIME,
    
    -- Employment Equity
    employment_equity_intro TEXT,
    employment_equity_statement TEXT,
    designated_groups JSONB, -- Array of designated groups (women, Indigenous people, etc.)
    
    -- Competition Notes
    eligibility_list_text TEXT,
    classification_flex_text TEXT,
    competition_usage_text TEXT,
    
    -- Position Overview
    position_summary_paragraphs JSONB, -- Array of summary paragraphs
    
    -- Benefits
    benefits_summary TEXT,
    benefits_items JSONB, -- Array of benefit items
    
    -- Conditions of Employment
    conditions_heading TEXT,
    conditions_items JSONB, -- Array of condition items
    
    -- Qualifications
    qualifications_heading TEXT,
    essential_qualifications JSONB, -- Array of essential qualification items
    desired_qualifications JSONB, -- Array of desired qualification items
    qualifications_equivalency_text TEXT,
    
    -- Duties
    duties_heading TEXT,
    duties_intro TEXT,
    duties_items JSONB, -- Array of duty items
    
    -- Application Instructions
    application_form_required BOOLEAN DEFAULT FALSE,
    application_form_link_text TEXT,
    application_form_url TEXT,
    application_instructions JSONB, -- Array of instruction paragraphs
    accommodation_text TEXT,
    grievance_notice TEXT,
    contact_note TEXT,
    
    -- Apply To Block
    apply_to_unit TEXT,
    apply_to_branch TEXT,
    apply_to_address JSONB, -- Array of address lines
    apply_to_phone TEXT,
    apply_to_fax TEXT,
    apply_to_email TEXT,
    
    -- Scraping Metadata
    search_keyword TEXT,
    matched_keyword TEXT,
    match_score INTEGER,
    scraped_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_man_jobs_job_id ON public.man_jobs(job_id);
CREATE INDEX idx_man_jobs_job_title ON public.man_jobs(job_title);
CREATE INDEX idx_man_jobs_advertisement_number ON public.man_jobs(advertisement_number);
CREATE INDEX idx_man_jobs_classification_code ON public.man_jobs(classification_code);
CREATE INDEX idx_man_jobs_closing_date ON public.man_jobs(closing_date);
CREATE INDEX idx_man_jobs_salary_min ON public.man_jobs(salary_min);
CREATE INDEX idx_man_jobs_salary_max ON public.man_jobs(salary_max);
CREATE INDEX idx_man_jobs_scraped_at ON public.man_jobs(scraped_at);
CREATE INDEX idx_man_jobs_search_keyword ON public.man_jobs(search_keyword);

-- Create GIN indexes for JSONB columns for efficient querying
CREATE INDEX idx_man_jobs_departments_gin ON public.man_jobs USING GIN(departments);
CREATE INDEX idx_man_jobs_locations_gin ON public.man_jobs USING GIN(locations);
CREATE INDEX idx_man_jobs_employment_types_gin ON public.man_jobs USING GIN(employment_types);
CREATE INDEX idx_man_jobs_essential_quals_gin ON public.man_jobs USING GIN(essential_qualifications);
CREATE INDEX idx_man_jobs_desired_quals_gin ON public.man_jobs USING GIN(desired_qualifications);

-- Create full-text search indexes
CREATE INDEX idx_man_jobs_job_title_fts ON public.man_jobs USING GIN(to_tsvector('english', job_title));
CREATE INDEX idx_man_jobs_position_summary_fts ON public.man_jobs USING GIN(to_tsvector('english', COALESCE(position_summary_paragraphs::text, '')));
CREATE INDEX idx_man_jobs_essential_quals_fts ON public.man_jobs USING GIN(to_tsvector('english', COALESCE(essential_qualifications::text, '')));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_man_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_man_jobs_updated_at
    BEFORE UPDATE ON public.man_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_man_jobs_updated_at();

-- Enable Row Level Security
ALTER TABLE public.man_jobs ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow public read access
CREATE POLICY "Allow public read access" ON public.man_jobs
    FOR SELECT
    USING (true);

-- Create a policy to allow authenticated users to insert
CREATE POLICY "Allow authenticated insert" ON public.man_jobs
    FOR INSERT
    WITH CHECK (true);

-- Create a policy to allow authenticated users to update
CREATE POLICY "Allow authenticated update" ON public.man_jobs
    FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- Add comments to document the table
COMMENT ON TABLE public.man_jobs IS 'Manitoba Government job postings scraped from jobsearch.gov.mb.ca';
COMMENT ON COLUMN public.man_jobs.job_id IS 'Unique job identifier from Manitoba job search system';
COMMENT ON COLUMN public.man_jobs.employment_types IS 'Array of employment types (e.g., Regular/full-time, Term, Casual)';
COMMENT ON COLUMN public.man_jobs.departments IS 'Array of government departments';
COMMENT ON COLUMN public.man_jobs.divisions IS 'Array of divisions within departments';
COMMENT ON COLUMN public.man_jobs.locations IS 'Array of work locations';
COMMENT ON COLUMN public.man_jobs.designated_groups IS 'Employment equity designated groups (women, Indigenous people, persons with disabilities, visible minorities)';
COMMENT ON COLUMN public.man_jobs.essential_qualifications IS 'Array of essential qualification requirements';
COMMENT ON COLUMN public.man_jobs.desired_qualifications IS 'Array of desired/asset qualifications';
COMMENT ON COLUMN public.man_jobs.duties_items IS 'Array of job duty descriptions';
COMMENT ON COLUMN public.man_jobs.conditions_items IS 'Array of conditions of employment';
