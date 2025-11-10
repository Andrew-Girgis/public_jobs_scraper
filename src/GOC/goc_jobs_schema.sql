-- ============================================================================
-- Government of Canada Jobs Table Schema
-- ============================================================================
-- This schema defines the PostgreSQL table structure for storing GC Jobs data.
-- It supports three different page structures (structure_1, structure_2, and
-- external_redirect) in a unified format.
--
-- Compatible with: PostgreSQL 12+ (Supabase)
-- ============================================================================

-- Drop existing table if you want to start fresh (CAUTION: this deletes data!)
-- DROP TABLE IF EXISTS jobs CASCADE;

-- Create the main jobs table
CREATE TABLE IF NOT EXISTS goc_jobs (
  -- Primary identification
  poster_id               TEXT PRIMARY KEY,
  url                     TEXT NOT NULL,

  -- Job basics
  title                   TEXT,
  department              TEXT,
  branch                  TEXT,

  -- Location
  city                    TEXT,
  province                TEXT,
  location_raw            TEXT,

  -- Classification
  classification_group    TEXT,
  classification_level    TEXT,
  classification_raw      TEXT,

  -- Dates
  closing_date            TIMESTAMPTZ,
  closing_time_raw        TEXT,
  date_modified           TIMESTAMPTZ,

  -- Salary
  salary_min              NUMERIC(10, 2),
  salary_max              NUMERIC(10, 2),
  salary_raw              TEXT,

  -- Application details
  who_can_apply           TEXT,
  employment_types        TEXT,
  positions_to_fill       INTEGER,

  -- Language requirements
  language_requirements_raw TEXT,

  -- External link information
  is_external_link        BOOLEAN DEFAULT FALSE,
  external_redirect_url   TEXT,
  external_job_title      TEXT,

  -- Scraping metadata
  search_title            TEXT,
  search_type             TEXT,
  scraped_at              TIMESTAMPTZ,
  structure_type          TEXT,

  -- Detailed information stored as JSON
  -- Contains: sections, qualifications, and contact information
  details                 JSONB
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Index on closing_date for filtering active postings
CREATE INDEX IF NOT EXISTS idx_goc_jobs_closing_date ON goc_jobs(closing_date);

-- Index on department for department-specific queries
CREATE INDEX IF NOT EXISTS idx_goc_jobs_department ON goc_jobs(department);

-- Index on classification for job type queries
CREATE INDEX IF NOT EXISTS idx_goc_jobs_classification_group ON goc_jobs(classification_group);
CREATE INDEX IF NOT EXISTS idx_goc_jobs_classification_level ON goc_jobs(classification_level);

-- Index on scraped_at for finding recently updated jobs
CREATE INDEX IF NOT EXISTS idx_goc_jobs_scraped_at ON goc_jobs(scraped_at DESC);

-- Index on structure_type for analytics
CREATE INDEX IF NOT EXISTS idx_goc_jobs_structure_type ON goc_jobs(structure_type);

-- Index on is_external_link for filtering external postings
CREATE INDEX IF NOT EXISTS idx_goc_jobs_is_external_link ON goc_jobs(is_external_link);

-- GIN index on details JSONB for fast JSON queries
CREATE INDEX IF NOT EXISTS idx_goc_jobs_details_gin ON goc_jobs USING GIN(details);

-- Full-text search index on title
CREATE INDEX IF NOT EXISTS idx_goc_jobs_title_search ON goc_jobs USING GIN(to_tsvector('english', COALESCE(title, '')));

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE goc_jobs IS 'Government of Canada job postings scraped from GC Jobs portal. Supports three structure types: structure_1 (new layout), structure_2 (classic layout), and external_redirect (external job boards).';

COMMENT ON COLUMN goc_jobs.poster_id IS 'Unique identifier for the job posting (e.g., 2370982)';
COMMENT ON COLUMN goc_jobs.url IS 'Full URL to the job posting on GC Jobs';
COMMENT ON COLUMN goc_jobs.title IS 'Job title as displayed on the posting';
COMMENT ON COLUMN goc_jobs.department IS 'Government department name';
COMMENT ON COLUMN goc_jobs.branch IS 'Department branch or division';
COMMENT ON COLUMN goc_jobs.city IS 'City where the job is located';
COMMENT ON COLUMN goc_jobs.province IS 'Province where the job is located';
COMMENT ON COLUMN goc_jobs.location_raw IS 'Raw location string from the posting (e.g., "Gatineau (Québec)")';
COMMENT ON COLUMN goc_jobs.classification_group IS 'Job classification group code (e.g., EC, PM, IT)';
COMMENT ON COLUMN goc_jobs.classification_level IS 'Job classification level (e.g., 01, 02, 03)';
COMMENT ON COLUMN goc_jobs.classification_raw IS 'Raw classification string (e.g., "EC-02")';
COMMENT ON COLUMN goc_jobs.closing_date IS 'Application deadline with time (ISO 8601 timestamp with timezone)';
COMMENT ON COLUMN goc_jobs.closing_time_raw IS 'Raw closing time string with timezone (e.g., "23:59, Pacific Time")';
COMMENT ON COLUMN goc_jobs.date_modified IS 'Date the posting was last modified (ISO 8601 timestamp with timezone)';
COMMENT ON COLUMN goc_jobs.salary_min IS 'Minimum salary in Canadian dollars (supports decimals for hourly rates)';
COMMENT ON COLUMN goc_jobs.salary_max IS 'Maximum salary in Canadian dollars (supports decimals for hourly rates)';
COMMENT ON COLUMN goc_jobs.salary_raw IS 'Raw salary string from the posting';
COMMENT ON COLUMN goc_jobs.who_can_apply IS 'Eligibility criteria text';
COMMENT ON COLUMN goc_jobs.employment_types IS 'Types of employment (e.g., "Acting; Indeterminate; Specified period")';
COMMENT ON COLUMN goc_jobs.positions_to_fill IS 'Number of positions available';
COMMENT ON COLUMN goc_jobs.language_requirements_raw IS 'Language requirement text';
COMMENT ON COLUMN goc_jobs.is_external_link IS 'True if this posting redirects to an external job board';
COMMENT ON COLUMN goc_jobs.external_redirect_url IS 'URL to external job board (if applicable)';
COMMENT ON COLUMN goc_jobs.external_job_title IS 'Job title on external site (if applicable)';
COMMENT ON COLUMN goc_jobs.search_title IS 'Search query term that found this posting';
COMMENT ON COLUMN goc_jobs.search_type IS 'Type of search run (e.g., "production", "dev")';
COMMENT ON COLUMN goc_jobs.scraped_at IS 'Timestamp when the job was scraped (UTC)';
COMMENT ON COLUMN goc_jobs.structure_type IS 'Page structure type: structure_1, structure_2, or external_redirect';
COMMENT ON COLUMN goc_jobs.details IS 'JSONB object containing sections, qualifications, and contact information';

-- ============================================================================
-- Example Upsert Pattern
-- ============================================================================
-- Use this pattern in your application code to insert or update jobs.
-- The ON CONFLICT clause ensures that if a job with the same poster_id
-- already exists, it will be updated with new data instead of causing an error.

/*
INSERT INTO goc_jobs (
  poster_id,
  url,
  title,
  department,
  branch,
  city,
  province,
  location_raw,
  classification_group,
  classification_level,
  classification_raw,
  closing_date,
  closing_time_raw,
  date_modified,
  salary_min,
  salary_max,
  salary_raw,
  who_can_apply,
  employment_types,
  positions_to_fill,
  language_requirements_raw,
  is_external_link,
  external_redirect_url,
  external_job_title,
  search_title,
  search_type,
  scraped_at,
  structure_type,
  details
)
VALUES (
  $1,   -- poster_id
  $2,   -- url
  $3,   -- title
  $4,   -- department
  $5,   -- branch
  $6,   -- city
  $7,   -- province
  $8,   -- location_raw
  $9,   -- classification_group
  $10,  -- classification_level
  $11,  -- classification_raw
  $12,  -- closing_date
  $13,  -- closing_time_raw
  $14,  -- date_modified
  $15,  -- salary_min
  $16,  -- salary_max
  $17,  -- salary_raw
  $18,  -- who_can_apply
  $19,  -- employment_types
  $20,  -- positions_to_fill
  $21,  -- language_requirements_raw
  $22,  -- is_external_link
  $23,  -- external_redirect_url
  $24,  -- external_job_title
  $25,  -- search_title
  $26,  -- search_type
  $27,  -- scraped_at
  $28,  -- structure_type
  $29   -- details (JSONB)
)
ON CONFLICT (poster_id) 
DO UPDATE SET
  url = EXCLUDED.url,
  title = EXCLUDED.title,
  department = EXCLUDED.department,
  branch = EXCLUDED.branch,
  city = EXCLUDED.city,
  province = EXCLUDED.province,
  location_raw = EXCLUDED.location_raw,
  classification_group = EXCLUDED.classification_group,
  classification_level = EXCLUDED.classification_level,
  classification_raw = EXCLUDED.classification_raw,
  closing_date = EXCLUDED.closing_date,
  closing_time_raw = EXCLUDED.closing_time_raw,
  date_modified = EXCLUDED.date_modified,
  salary_min = EXCLUDED.salary_min,
  salary_max = EXCLUDED.salary_max,
  salary_raw = EXCLUDED.salary_raw,
  who_can_apply = EXCLUDED.who_can_apply,
  employment_types = EXCLUDED.employment_types,
  positions_to_fill = EXCLUDED.positions_to_fill,
  language_requirements_raw = EXCLUDED.language_requirements_raw,
  is_external_link = EXCLUDED.is_external_link,
  external_redirect_url = EXCLUDED.external_redirect_url,
  external_job_title = EXCLUDED.external_job_title,
  search_title = EXCLUDED.search_title,
  search_type = EXCLUDED.search_type,
  scraped_at = EXCLUDED.scraped_at,
  structure_type = EXCLUDED.structure_type,
  details = EXCLUDED.details;
*/

-- ============================================================================
-- Example Queries
-- ============================================================================

-- Find all jobs closing soon
-- SELECT poster_id, title, department, closing_date 
-- FROM goc_jobs 
-- WHERE closing_date >= CURRENT_DATE 
--   AND closing_date <= CURRENT_DATE + INTERVAL '7 days'
-- ORDER BY closing_date;

-- Find all external job postings
-- SELECT poster_id, external_job_title, external_redirect_url 
-- FROM goc_jobs 
-- WHERE is_external_link = TRUE;

-- Find jobs by classification
-- SELECT poster_id, title, classification_raw, salary_raw
-- FROM goc_jobs
-- WHERE classification_group = 'EC'
--   AND classification_level = '02';

-- Search within JSONB details
-- SELECT poster_id, title, department
-- FROM goc_jobs
-- WHERE details->'sections'->>'duties' ILIKE '%data analysis%';

-- Count jobs by structure type
-- SELECT structure_type, COUNT(*) 
-- FROM goc_jobs 
-- GROUP BY structure_type;
