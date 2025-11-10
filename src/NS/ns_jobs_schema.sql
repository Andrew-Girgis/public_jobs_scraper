-- Nova Scotia Government Jobs Table Schema
-- Database: Supabase PostgreSQL
-- Table: ns_jobs

CREATE TABLE IF NOT EXISTS ns_jobs (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    
    -- Source Information
    jurisdiction TEXT DEFAULT 'Nova Scotia',
    job_board TEXT DEFAULT 'Government of Nova Scotia',
    url TEXT NOT NULL,
    
    -- Metadata
    job_title TEXT NOT NULL,
    classification TEXT,
    competition_number TEXT,
    department TEXT,
    location TEXT,
    type_of_employment TEXT,
    union_status TEXT,
    closing_date TIMESTAMPTZ,
    closing_time TEXT,
    closing_timezone TEXT DEFAULT 'Atlantic Time',
    
    -- Compensation
    pay_grade TEXT,
    salary_range_raw TEXT,
    salary_min NUMERIC(10, 2),
    salary_max NUMERIC(10, 2),
    salary_frequency TEXT,
    salary_currency TEXT DEFAULT 'CAD',
    
    -- Content Sections (TEXT fields for long content)
    about_us_heading TEXT,
    about_us_body TEXT,
    
    about_opportunity_heading TEXT,
    about_opportunity_body TEXT,
    
    primary_accountabilities_heading TEXT,
    primary_accountabilities_intro TEXT,
    primary_accountabilities_bullets JSONB DEFAULT '[]',
    
    qualifications_heading TEXT,
    qualifications_requirements_intro TEXT,
    qualifications_required_education TEXT,
    qualifications_required_experience TEXT,
    qualifications_required_bullets JSONB DEFAULT '[]',
    qualifications_additional_skills_bullets JSONB DEFAULT '[]',
    qualifications_asset_heading TEXT,
    qualifications_asset_bullets JSONB DEFAULT '[]',
    qualifications_equivalency_heading TEXT,
    qualifications_equivalency_text TEXT,
    
    benefits_heading TEXT,
    benefits_body TEXT,
    benefits_link_text TEXT,
    benefits_link_url TEXT,
    
    working_conditions_heading TEXT,
    working_conditions_body TEXT,
    
    additional_information_heading TEXT,
    additional_information_body TEXT,
    
    what_we_offer_heading TEXT,
    what_we_offer_bullets JSONB DEFAULT '[]',
    
    -- Statements
    employment_equity_heading TEXT,
    employment_equity_body TEXT,
    
    accommodation_heading TEXT,
    accommodation_body TEXT,
    
    -- Application Instructions
    internal_applicants_text TEXT,
    external_applicants_text TEXT,
    incomplete_applications_note TEXT,
    contact_email TEXT,
    
    -- Scraping Metadata
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    search_keyword TEXT,
    matched_keyword TEXT,
    match_score NUMERIC(5, 2),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ns_jobs_job_id ON ns_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_ns_jobs_job_title ON ns_jobs(job_title);
CREATE INDEX IF NOT EXISTS idx_ns_jobs_department ON ns_jobs(department);
CREATE INDEX IF NOT EXISTS idx_ns_jobs_location ON ns_jobs(location);
CREATE INDEX IF NOT EXISTS idx_ns_jobs_closing_date ON ns_jobs(closing_date);
CREATE INDEX IF NOT EXISTS idx_ns_jobs_matched_keyword ON ns_jobs(matched_keyword);
CREATE INDEX IF NOT EXISTS idx_ns_jobs_scraped_at ON ns_jobs(scraped_at);
CREATE INDEX IF NOT EXISTS idx_ns_jobs_created_at ON ns_jobs(created_at);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_ns_jobs_job_title_fts ON ns_jobs USING gin(to_tsvector('english', job_title));
CREATE INDEX IF NOT EXISTS idx_ns_jobs_about_us_fts ON ns_jobs USING gin(to_tsvector('english', COALESCE(about_us_body, '')));
CREATE INDEX IF NOT EXISTS idx_ns_jobs_about_opportunity_fts ON ns_jobs USING gin(to_tsvector('english', COALESCE(about_opportunity_body, '')));

-- Trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ns_jobs_updated_at BEFORE UPDATE ON ns_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE ns_jobs IS 'Nova Scotia government job postings scraped from jobs.novascotia.ca';
COMMENT ON COLUMN ns_jobs.job_id IS 'Unique job identifier from Nova Scotia job board';
COMMENT ON COLUMN ns_jobs.search_keyword IS 'The keyword used in the search query to find this job';
COMMENT ON COLUMN ns_jobs.matched_keyword IS 'The keyword from list-of-jobs.txt that matched via token matching';
COMMENT ON COLUMN ns_jobs.match_score IS 'Token matching score (0-100)';
COMMENT ON COLUMN ns_jobs.closing_date IS 'Job posting closing date and time in Atlantic timezone';
COMMENT ON COLUMN ns_jobs.scraped_at IS 'When this job was scraped from the website';

-- Row Level Security (RLS) - Enable if using Supabase auth
-- ALTER TABLE ns_jobs ENABLE ROW LEVEL SECURITY;

-- Example RLS policy for public read access
-- CREATE POLICY "Allow public read access" ON ns_jobs FOR SELECT USING (true);

-- Example RLS policy for authenticated insert/update
-- CREATE POLICY "Allow authenticated insert" ON ns_jobs FOR INSERT WITH CHECK (auth.role() = 'authenticated');
-- CREATE POLICY "Allow authenticated update" ON ns_jobs FOR UPDATE USING (auth.role() = 'authenticated');
