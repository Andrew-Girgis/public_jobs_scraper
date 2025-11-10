-- Alberta Public Service Jobs Table Schema
-- Drop existing table if it exists
DROP TABLE IF EXISTS public.ab_jobs CASCADE;

CREATE TABLE IF NOT EXISTS public.ab_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    
    -- Job Identification
    job_id TEXT UNIQUE NOT NULL,
    job_requisition_id TEXT,
    job_title TEXT NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'Alberta',
    job_board TEXT DEFAULT 'Alberta Public Service Careers',
    company TEXT DEFAULT 'Government of Alberta',
    url TEXT NOT NULL,
    
    -- Classification and Job Details
    classification TEXT,
    ministry TEXT,
    location TEXT,
    location_line TEXT, -- e.g., "Edmonton, AB"
    full_or_part_time TEXT,
    hours_of_work TEXT, -- e.g., "36.25 hours per week"
    permanent_or_temporary TEXT,
    scope TEXT, -- e.g., "Open Competition"
    
    -- Dates
    posting_date TEXT,
    closing_date TEXT,
    
    -- Salary Information
    salary_raw_text TEXT,
    salary_biweekly_min DECIMAL(12,2),
    salary_biweekly_max DECIMAL(12,2),
    salary_annual_min DECIMAL(12,2),
    salary_annual_max DECIMAL(12,2),
    salary_currency TEXT DEFAULT 'CAD',
    salary_primary_frequency TEXT, -- e.g., "bi-weekly"
    
    -- Ministry/Organization Overview
    ministry_overview_heading TEXT,
    ministry_overview_body JSONB, -- Array of paragraphs
    
    -- Role Responsibilities
    role_responsibilities_heading TEXT DEFAULT 'Role Responsibilities',
    role_responsibilities_tagline TEXT,
    role_responsibilities_intro JSONB, -- Array of intro paragraphs
    role_responsibilities_groups JSONB, -- Array of {heading, items} objects
    job_description_link_text TEXT,
    job_description_url TEXT,
    
    -- APS Competencies
    aps_competencies_heading TEXT DEFAULT 'APS Competencies',
    aps_competencies_description TEXT,
    aps_competencies_items JSONB, -- Array of competency items
    aps_competencies_url TEXT DEFAULT 'https://www.alberta.ca/system/files/custom_downloaded_images/psc-alberta-public-service-competency-model.pdf',
    
    -- Qualifications
    qualifications_heading TEXT DEFAULT 'Qualifications',
    required_education JSONB, -- Array of education requirements
    required_experience JSONB, -- Array of experience requirements
    required_other JSONB, -- Array of other requirements (skills, abilities, etc.)
    equivalency_text TEXT,
    equivalency_rules JSONB, -- Array of equivalency rules
    asset_qualifications JSONB, -- Array of asset/nice-to-have qualifications
    minimum_recruitment_standards_url TEXT DEFAULT 'https://www.alberta.ca/alberta-public-service-minimum-recruitment-standards',
    
    -- Notes Section
    notes_heading TEXT DEFAULT 'Notes',
    notes_employment_term TEXT,
    notes_location_reminder TEXT,
    notes_assessment_info JSONB, -- Array of assessment information
    notes_security_screening JSONB, -- Array of security screening notes
    notes_reuse_competition JSONB, -- Array of competition reuse notes
    notes_costs JSONB, -- Array of cost-related notes
    notes_benefits_resources JSONB, -- Array of {label, url} objects for benefits/resources links
    
    -- How to Apply
    how_to_apply_heading TEXT DEFAULT 'How To Apply',
    how_to_apply_instructions JSONB, -- Array of instruction paragraphs
    job_application_resources_url TEXT DEFAULT 'https://www.alberta.ca/job-application-resources#before',
    recruitment_principles_url TEXT DEFAULT 'https://www.alberta.ca/recruitment-principles',
    iqas_recommended BOOLEAN DEFAULT TRUE,
    iqas_url TEXT DEFAULT 'https://www.alberta.ca/international-qualifications-assessment.aspx',
    alliance_url TEXT DEFAULT 'https://canalliance.org/en/default.html',
    
    -- Closing Statement
    closing_reuse_competition_note TEXT,
    closing_thanks_screening_note TEXT,
    closing_contact_name TEXT,
    closing_contact_email TEXT,
    closing_accommodation_note TEXT,
    
    -- Diversity and Inclusion
    diversity_statement TEXT,
    diversity_policy_url TEXT DEFAULT 'https://www.alberta.ca/diversity-inclusion-policy.aspx',
    
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
CREATE INDEX idx_ab_jobs_job_id ON public.ab_jobs(job_id);
CREATE INDEX idx_ab_jobs_job_requisition_id ON public.ab_jobs(job_requisition_id);
CREATE INDEX idx_ab_jobs_job_title ON public.ab_jobs(job_title);
CREATE INDEX idx_ab_jobs_classification ON public.ab_jobs(classification);
CREATE INDEX idx_ab_jobs_ministry ON public.ab_jobs(ministry);
CREATE INDEX idx_ab_jobs_location ON public.ab_jobs(location);
CREATE INDEX idx_ab_jobs_closing_date ON public.ab_jobs(closing_date);
CREATE INDEX idx_ab_jobs_salary_annual_min ON public.ab_jobs(salary_annual_min);
CREATE INDEX idx_ab_jobs_salary_annual_max ON public.ab_jobs(salary_annual_max);
CREATE INDEX idx_ab_jobs_salary_biweekly_min ON public.ab_jobs(salary_biweekly_min);
CREATE INDEX idx_ab_jobs_salary_biweekly_max ON public.ab_jobs(salary_biweekly_max);
CREATE INDEX idx_ab_jobs_scraped_at ON public.ab_jobs(scraped_at);
CREATE INDEX idx_ab_jobs_search_keyword ON public.ab_jobs(search_keyword);
CREATE INDEX idx_ab_jobs_matched_keyword ON public.ab_jobs(matched_keyword);
CREATE INDEX idx_ab_jobs_match_score ON public.ab_jobs(match_score);
CREATE INDEX idx_ab_jobs_permanent_or_temporary ON public.ab_jobs(permanent_or_temporary);
CREATE INDEX idx_ab_jobs_full_or_part_time ON public.ab_jobs(full_or_part_time);

-- Create GIN indexes for JSONB columns for efficient querying
CREATE INDEX idx_ab_jobs_ministry_overview_gin ON public.ab_jobs USING GIN(ministry_overview_body);
CREATE INDEX idx_ab_jobs_responsibilities_groups_gin ON public.ab_jobs USING GIN(role_responsibilities_groups);
CREATE INDEX idx_ab_jobs_competencies_gin ON public.ab_jobs USING GIN(aps_competencies_items);
CREATE INDEX idx_ab_jobs_required_education_gin ON public.ab_jobs USING GIN(required_education);
CREATE INDEX idx_ab_jobs_required_experience_gin ON public.ab_jobs USING GIN(required_experience);
CREATE INDEX idx_ab_jobs_required_other_gin ON public.ab_jobs USING GIN(required_other);
CREATE INDEX idx_ab_jobs_asset_qualifications_gin ON public.ab_jobs USING GIN(asset_qualifications);
CREATE INDEX idx_ab_jobs_benefits_resources_gin ON public.ab_jobs USING GIN(notes_benefits_resources);

-- Create full-text search indexes
CREATE INDEX idx_ab_jobs_job_title_fts ON public.ab_jobs USING GIN(to_tsvector('english', job_title));
CREATE INDEX idx_ab_jobs_ministry_overview_fts ON public.ab_jobs USING GIN(to_tsvector('english', COALESCE(ministry_overview_body::text, '')));
CREATE INDEX idx_ab_jobs_responsibilities_fts ON public.ab_jobs USING GIN(to_tsvector('english', COALESCE(role_responsibilities_intro::text, '')));
CREATE INDEX idx_ab_jobs_required_exp_fts ON public.ab_jobs USING GIN(to_tsvector('english', COALESCE(required_experience::text, '')));
CREATE INDEX idx_ab_jobs_required_education_fts ON public.ab_jobs USING GIN(to_tsvector('english', COALESCE(required_education::text, '')));

-- Create a trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_ab_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_ab_jobs_updated_at
    BEFORE UPDATE ON public.ab_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_ab_jobs_updated_at();

-- Enable Row Level Security
ALTER TABLE public.ab_jobs ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow public read access
CREATE POLICY "Allow public read access" ON public.ab_jobs
    FOR SELECT
    USING (true);

-- Create a policy to allow authenticated users to insert
CREATE POLICY "Allow authenticated insert" ON public.ab_jobs
    FOR INSERT
    WITH CHECK (true);

-- Create a policy to allow authenticated users to update
CREATE POLICY "Allow authenticated update" ON public.ab_jobs
    FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- Add comments to document the table
COMMENT ON TABLE public.ab_jobs IS 'Alberta Public Service job postings scraped from jobpostings.alberta.ca';
COMMENT ON COLUMN public.ab_jobs.job_id IS 'Unique job identifier from Alberta job posting system';
COMMENT ON COLUMN public.ab_jobs.job_requisition_id IS 'Internal job requisition ID number';
COMMENT ON COLUMN public.ab_jobs.classification IS 'Job classification (e.g., "Finance 3", "Policy 3")';
COMMENT ON COLUMN public.ab_jobs.ministry IS 'Ministry or department responsible for the position';
COMMENT ON COLUMN public.ab_jobs.scope IS 'Competition scope (e.g., "Open Competition", "Internal Competition")';
COMMENT ON COLUMN public.ab_jobs.salary_biweekly_min IS 'Minimum bi-weekly salary in CAD';
COMMENT ON COLUMN public.ab_jobs.salary_biweekly_max IS 'Maximum bi-weekly salary in CAD';
COMMENT ON COLUMN public.ab_jobs.salary_annual_min IS 'Minimum annual salary in CAD';
COMMENT ON COLUMN public.ab_jobs.salary_annual_max IS 'Maximum annual salary in CAD';
COMMENT ON COLUMN public.ab_jobs.ministry_overview_body IS 'Array of paragraphs describing the ministry or organization';
COMMENT ON COLUMN public.ab_jobs.role_responsibilities_groups IS 'Array of responsibility group objects with heading and items';
COMMENT ON COLUMN public.ab_jobs.aps_competencies_items IS 'Array of APS (Alberta Public Service) competencies';
COMMENT ON COLUMN public.ab_jobs.required_education IS 'Array of required education qualifications';
COMMENT ON COLUMN public.ab_jobs.required_experience IS 'Array of required experience qualifications';
COMMENT ON COLUMN public.ab_jobs.required_other IS 'Array of other required qualifications (skills, abilities, etc.)';
COMMENT ON COLUMN public.ab_jobs.asset_qualifications IS 'Array of nice-to-have/asset qualifications';
COMMENT ON COLUMN public.ab_jobs.equivalency_rules IS 'Array of equivalency rules for qualifications';
COMMENT ON COLUMN public.ab_jobs.notes_assessment_info IS 'Array of assessment process information';
COMMENT ON COLUMN public.ab_jobs.notes_security_screening IS 'Array of security screening requirements';
COMMENT ON COLUMN public.ab_jobs.notes_benefits_resources IS 'Array of benefits and resources link objects';
COMMENT ON COLUMN public.ab_jobs.iqas_recommended IS 'Whether International Qualifications Assessment Service (IQAS) is recommended';
COMMENT ON COLUMN public.ab_jobs.match_score IS 'Fuzzy matching score (0-100) indicating job title relevance to search keyword';
COMMENT ON COLUMN public.ab_jobs.diversity_statement IS 'Alberta Public Service diversity and inclusion statement';
