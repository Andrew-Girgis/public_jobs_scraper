-- Saskatchewan Government Jobs Table Schema
-- Drop existing table if it exists
CREATE TABLE IF NOT EXISTS sas_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    job_title TEXT NOT NULL,
    competition_number TEXT,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'Saskatchewan',
    job_board TEXT DEFAULT 'Government of Saskatchewan',
    url TEXT NOT NULL,
    
    -- Employment Details
    employment_type TEXT,
    location TEXT,
    ministry TEXT,
    grade TEXT,
    hours_of_work TEXT,
    number_of_openings INTEGER,
    
    -- Salary Information
    salary_range TEXT,
    salary_min DECIMAL(10,3),
    salary_max DECIMAL(10,3),
    salary_frequency TEXT, -- 'Hourly' or 'Monthly'
    salary_supplement TEXT,
    
    -- Dates
    closing_date TIMESTAMP WITH TIME ZONE,
    
    -- Job Content
    ministry_description TEXT,
    full_description TEXT,
    
    -- The Opportunity Section
    opportunity_intro TEXT,
    opportunity_responsibilities TEXT,
    
    -- Responsibilities Breakdown (5 categories)
    strategic_leadership_planning TEXT,
    technical_oversight TEXT,
    information_knowledge_management TEXT,
    stakeholder_engagement_collaboration TEXT,
    team_resource_management TEXT,
    
    -- Qualifications
    ideal_candidate TEXT,
    qualifications_intro TEXT,
    required_qualifications JSONB, -- Array of qualifications
    education_requirements TEXT,
    
    -- Benefits
    what_we_offer TEXT,
    benefits_list JSONB, -- Array of benefits
    
    -- Additional Information
    diversity_statement TEXT,
    additional_notes TEXT,
    
    -- Scraping Metadata
    search_keyword TEXT,
    matched_keyword TEXT,
    match_score INTEGER,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_sas_jobs_job_id ON public.sas_jobs(job_id);
CREATE INDEX idx_sas_jobs_job_title ON public.sas_jobs(job_title);
CREATE INDEX idx_sas_jobs_ministry ON public.sas_jobs(ministry);
CREATE INDEX idx_sas_jobs_location ON public.sas_jobs(location);
CREATE INDEX idx_sas_jobs_employment_type ON public.sas_jobs(employment_type);
CREATE INDEX idx_sas_jobs_closing_date ON public.sas_jobs(closing_date);
CREATE INDEX idx_sas_jobs_salary_min ON public.sas_jobs(salary_min);
CREATE INDEX idx_sas_jobs_salary_max ON public.sas_jobs(salary_max);
CREATE INDEX idx_sas_jobs_scraped_at ON public.sas_jobs(scraped_at);
CREATE INDEX idx_sas_jobs_search_keyword ON public.sas_jobs(search_keyword);

-- Create full-text search index for job descriptions
CREATE INDEX idx_sas_jobs_full_description_fts ON public.sas_jobs USING GIN(to_tsvector('english', full_description));
CREATE INDEX idx_sas_jobs_job_title_fts ON public.sas_jobs USING GIN(to_tsvector('english', job_title));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_sas_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_sas_jobs_updated_at
    BEFORE UPDATE ON public.sas_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_sas_jobs_updated_at();

-- Enable Row Level Security (optional, if needed)
ALTER TABLE public.sas_jobs ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow public read access (adjust as needed)
CREATE POLICY "Allow public read access" ON public.sas_jobs
    FOR SELECT
    USING (true);

-- Create a policy to allow authenticated users to insert (adjust as needed)
CREATE POLICY "Allow authenticated insert" ON public.sas_jobs
    FOR INSERT
    WITH CHECK (true);

-- Add comments to document the table
COMMENT ON TABLE public.sas_jobs IS 'Saskatchewan Government job postings scraped from govskpsc.taleo.net';
COMMENT ON COLUMN public.sas_jobs.job_id IS 'Unique job identifier from Taleo system';
COMMENT ON COLUMN public.sas_jobs.competition_number IS 'Government competition/requisition number';
COMMENT ON COLUMN public.sas_jobs.grade IS 'Job classification/grade (e.g., SGEU.09)';
COMMENT ON COLUMN public.sas_jobs.hours_of_work IS 'Work schedule description';
COMMENT ON COLUMN public.sas_jobs.salary_frequency IS 'Hourly or Monthly salary frequency';
COMMENT ON COLUMN public.sas_jobs.strategic_leadership_planning IS 'Strategic Leadership & Planning responsibilities';
COMMENT ON COLUMN public.sas_jobs.technical_oversight IS 'Technical Oversight responsibilities';
COMMENT ON COLUMN public.sas_jobs.information_knowledge_management IS 'Information & Knowledge Management responsibilities';
COMMENT ON COLUMN public.sas_jobs.stakeholder_engagement_collaboration IS 'Stakeholder Engagement & Collaboration responsibilities';
COMMENT ON COLUMN public.sas_jobs.team_resource_management IS 'Team & Resource Management responsibilities';
