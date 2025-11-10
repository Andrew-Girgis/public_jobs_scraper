-- British Columbia Public Service Jobs Table Schema
-- Drop existing table if it exists
CREATE TABLE IF NOT EXISTS public.bc_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    posting_id TEXT,
    posting_title TEXT NOT NULL,
    job_title TEXT,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'British Columbia',
    job_board TEXT DEFAULT 'BC Public Service',
    organization TEXT,
    url TEXT NOT NULL,
    
    -- Classification Details
    position_classification TEXT,
    classification_code TEXT,
    "union" TEXT,
    job_type TEXT, -- e.g., "Regular Full Time"
    job_category TEXT,
    
    -- Work Arrangements
    work_options TEXT, -- e.g., "Hybrid", "Remote", "On-site"
    locations JSONB, -- Array of work locations
    
    -- Ministry/Organization Structure
    ministry_organization TEXT,
    ministry_branch_division TEXT,
    
    -- Salary Information
    salary_raw_text TEXT,
    salary_min DECIMAL(12,2),
    salary_max DECIMAL(12,2),
    salary_frequency TEXT, -- 'per annum', 'per hour', etc.
    salary_currency TEXT DEFAULT 'CAD',
    temporary_market_adjustment TEXT, -- e.g., "9.9%"
    
    -- Dates
    close_date DATE,
    close_time TEXT DEFAULT '11:00 pm Pacific Time',
    temporary_end_date DATE, -- For temporary positions
    
    -- Amendments
    amendments JSONB, -- Array of amendment objects with date and description
    
    -- Job Summary Sections
    about_organization_heading TEXT,
    about_organization_body JSONB, -- Array of paragraphs
    about_business_unit_heading TEXT,
    about_business_unit_body JSONB, -- Array of paragraphs
    about_role_heading TEXT,
    about_role_body JSONB, -- Array of paragraphs
    special_conditions JSONB, -- Array of special condition statements
    eligibility_list_note TEXT,
    
    -- Education and Experience Requirements
    education_experience_paths JSONB, -- Array of {education, experience_years} objects
    equivalency_statement TEXT,
    recent_experience_note TEXT,
    
    -- Position Requirements
    position_requirements_heading TEXT DEFAULT 'Position requirements',
    required_experience_bullets JSONB, -- Array of required experience/qualification bullets
    preferred_experience_bullets JSONB, -- Array of preferred/nice-to-have bullets
    
    -- Application Requirements
    cover_letter_required BOOLEAN DEFAULT FALSE,
    resume_details_required BOOLEAN DEFAULT TRUE,
    other_documents JSONB, -- Array of other required documents
    
    -- Application Instructions
    application_instructions_heading TEXT DEFAULT 'Application instructions',
    evaluation_note TEXT,
    
    -- HR Contact Information
    hr_contact_name TEXT,
    hr_contact_title TEXT,
    hr_contact_email TEXT,
    
    -- Submission Details
    submission_system_name TEXT DEFAULT 'BC Public Service Recruitment System',
    submission_notes JSONB, -- Array of submission note paragraphs
    technical_help_email TEXT DEFAULT 'BCPSA.Hiring.Centre@gov.bc.ca',
    technical_help_notes JSONB, -- Array of technical help notes
    deadline_note TEXT DEFAULT 'Applications will be accepted until 11:00pm Pacific Time on the closing date of the competition.',
    accommodation_text TEXT,
    
    -- Working for BC Public Service Section
    diversity_statement TEXT,
    flexible_work_statement TEXT,
    
    -- Indigenous Applicant Advisory Service
    indigenous_service_available BOOLEAN DEFAULT TRUE,
    indigenous_service_description TEXT,
    indigenous_service_email TEXT,
    indigenous_service_phone TEXT,
    
    -- Employer Value Proposition
    employer_value_proposition JSONB, -- Array of value proposition statements
    
    -- Attachments
    attachment_files JSONB, -- Array of {label, path_or_url} objects for job description files
    
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
CREATE INDEX idx_bc_jobs_job_id ON public.bc_jobs(job_id);
CREATE INDEX idx_bc_jobs_posting_id ON public.bc_jobs(posting_id);
CREATE INDEX idx_bc_jobs_posting_title ON public.bc_jobs(posting_title);
CREATE INDEX idx_bc_jobs_job_title ON public.bc_jobs(job_title);
CREATE INDEX idx_bc_jobs_classification_code ON public.bc_jobs(classification_code);
CREATE INDEX idx_bc_jobs_close_date ON public.bc_jobs(close_date);
CREATE INDEX idx_bc_jobs_salary_min ON public.bc_jobs(salary_min);
CREATE INDEX idx_bc_jobs_salary_max ON public.bc_jobs(salary_max);
CREATE INDEX idx_bc_jobs_scraped_at ON public.bc_jobs(scraped_at);
CREATE INDEX idx_bc_jobs_search_keyword ON public.bc_jobs(search_keyword);
CREATE INDEX idx_bc_jobs_work_options ON public.bc_jobs(work_options);
CREATE INDEX idx_bc_jobs_job_type ON public.bc_jobs(job_type);
CREATE INDEX idx_bc_jobs_ministry_organization ON public.bc_jobs(ministry_organization);

-- Create GIN indexes for JSONB columns for efficient querying
CREATE INDEX idx_bc_jobs_locations_gin ON public.bc_jobs USING GIN(locations);
CREATE INDEX idx_bc_jobs_required_exp_gin ON public.bc_jobs USING GIN(required_experience_bullets);
CREATE INDEX idx_bc_jobs_preferred_exp_gin ON public.bc_jobs USING GIN(preferred_experience_bullets);
CREATE INDEX idx_bc_jobs_special_conditions_gin ON public.bc_jobs USING GIN(special_conditions);
CREATE INDEX idx_bc_jobs_education_paths_gin ON public.bc_jobs USING GIN(education_experience_paths);
CREATE INDEX idx_bc_jobs_attachments_gin ON public.bc_jobs USING GIN(attachment_files);

-- Create full-text search indexes
CREATE INDEX idx_bc_jobs_posting_title_fts ON public.bc_jobs USING GIN(to_tsvector('english', posting_title));
CREATE INDEX idx_bc_jobs_about_role_fts ON public.bc_jobs USING GIN(to_tsvector('english', COALESCE(about_role_body::text, '')));
CREATE INDEX idx_bc_jobs_required_exp_fts ON public.bc_jobs USING GIN(to_tsvector('english', COALESCE(required_experience_bullets::text, '')));
CREATE INDEX idx_bc_jobs_preferred_exp_fts ON public.bc_jobs USING GIN(to_tsvector('english', COALESCE(preferred_experience_bullets::text, '')));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_bc_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_bc_jobs_updated_at
    BEFORE UPDATE ON public.bc_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_bc_jobs_updated_at();

-- Enable Row Level Security
ALTER TABLE public.bc_jobs ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow public read access
CREATE POLICY "Allow public read access" ON public.bc_jobs
    FOR SELECT
    USING (true);

-- Create a policy to allow authenticated users to insert
CREATE POLICY "Allow authenticated insert" ON public.bc_jobs
    FOR INSERT
    WITH CHECK (true);

-- Create a policy to allow authenticated users to update
CREATE POLICY "Allow authenticated update" ON public.bc_jobs
    FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- Add comments to document the table
COMMENT ON TABLE public.bc_jobs IS 'British Columbia Public Service job postings scraped from bcpublicservice.hua.hrsmart.com';
COMMENT ON COLUMN public.bc_jobs.job_id IS 'Unique job identifier from BC HRsmart system';
COMMENT ON COLUMN public.bc_jobs.posting_id IS 'Posting identifier (may differ from job_id)';
COMMENT ON COLUMN public.bc_jobs.work_options IS 'Work arrangement options (Hybrid, Remote, On-site)';
COMMENT ON COLUMN public.bc_jobs.locations IS 'Array of work locations';
COMMENT ON COLUMN public.bc_jobs.temporary_market_adjustment IS 'Temporary market adjustment percentage (e.g., "9.9%")';
COMMENT ON COLUMN public.bc_jobs.amendments IS 'Array of job posting amendments with dates and descriptions';
COMMENT ON COLUMN public.bc_jobs.about_organization_body IS 'Array of paragraphs describing the organization';
COMMENT ON COLUMN public.bc_jobs.about_business_unit_body IS 'Array of paragraphs describing the business unit';
COMMENT ON COLUMN public.bc_jobs.about_role_body IS 'Array of paragraphs describing the role';
COMMENT ON COLUMN public.bc_jobs.special_conditions IS 'Array of special conditions statements';
COMMENT ON COLUMN public.bc_jobs.education_experience_paths IS 'Array of education/experience path objects with education and experience_years fields';
COMMENT ON COLUMN public.bc_jobs.required_experience_bullets IS 'Array of required experience and qualification bullets';
COMMENT ON COLUMN public.bc_jobs.preferred_experience_bullets IS 'Array of preferred/nice-to-have qualification bullets';
COMMENT ON COLUMN public.bc_jobs.other_documents IS 'Array of other required application documents';
COMMENT ON COLUMN public.bc_jobs.hr_contact_name IS 'Name of HR contact person (if available)';
COMMENT ON COLUMN public.bc_jobs.hr_contact_title IS 'Title of HR contact person';
COMMENT ON COLUMN public.bc_jobs.hr_contact_email IS 'Email of HR contact person';
COMMENT ON COLUMN public.bc_jobs.diversity_statement IS 'BC Public Service diversity and inclusion statement';
COMMENT ON COLUMN public.bc_jobs.flexible_work_statement IS 'Statement about flexible work arrangements';
COMMENT ON COLUMN public.bc_jobs.indigenous_service_description IS 'Description of Indigenous Applicant Advisory Service';
COMMENT ON COLUMN public.bc_jobs.indigenous_service_email IS 'Contact email for Indigenous Applicant Advisory Service';
COMMENT ON COLUMN public.bc_jobs.indigenous_service_phone IS 'Contact phone for Indigenous Applicant Advisory Service';
COMMENT ON COLUMN public.bc_jobs.employer_value_proposition IS 'Array of employer value proposition statements';
COMMENT ON COLUMN public.bc_jobs.attachment_files IS 'Array of attachment file objects with label and path_or_url fields';
