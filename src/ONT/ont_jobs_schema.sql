-- Ontario Jobs Table Schema
-- Matches the JSON structure from ont_scraper.py exactly

CREATE TABLE IF NOT EXISTS ont_jobs (
  id SERIAL NOT NULL,
  job_id VARCHAR(50) NOT NULL,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  organization VARCHAR(200),
  division VARCHAR(200),
  city VARCHAR(100),
  posting_status VARCHAR(50),
  position_language VARCHAR(100),
  job_term TEXT,
  job_code VARCHAR(50),
  salary VARCHAR(100),
  salary_min DECIMAL(10,2),
  salary_max DECIMAL(10,2),
  salary_period VARCHAR(20),
  apply_by TIMESTAMP,
  posted_on TIMESTAMP,
  position_details TEXT,
  compensation_group VARCHAR(200),
  work_hours VARCHAR(50),
  category VARCHAR(100),
  note TEXT,
  about_the_job TEXT,
  what_you_bring TEXT,
  mandatory_requirements TEXT,
  additional_info TEXT,
  how_to_apply TEXT,
  matched_keyword VARCHAR(200),
  match_score DECIMAL(5,2),
  scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT ont_jobs_pkey PRIMARY KEY (id),
  CONSTRAINT ont_jobs_job_id_key UNIQUE (job_id)
) TABLESPACE pg_default;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ont_jobs_job_id ON public.ont_jobs USING btree (job_id) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_ont_jobs_title ON public.ont_jobs USING btree (title) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_ont_jobs_city ON public.ont_jobs USING btree (city) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_ont_jobs_category ON public.ont_jobs USING btree (category) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_ont_jobs_scraped_at ON public.ont_jobs USING btree (scraped_at) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_ont_jobs_apply_by ON public.ont_jobs USING btree (apply_by) TABLESPACE pg_default;
CREATE INDEX IF NOT EXISTS idx_ont_jobs_matched_keyword ON public.ont_jobs USING btree (matched_keyword) TABLESPACE pg_default;

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_ont_jobs_updated_at 
BEFORE UPDATE ON ont_jobs 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();
