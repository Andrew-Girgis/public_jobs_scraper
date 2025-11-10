# Government Jobs Research Project

## Executive Summary

This research project systematically collects and analyzes technical government job postings across Canada, the United Kingdom, and Australia to understand differences in position classifications, compensation structures, and qualification requirements. The automated data collection system currently covers seven Canadian jurisdictions (federal and provincial), with 158 validated technical positions across 44 job categories.

## Research Objective

This project addresses a fundamental question in comparative public administration: **How do technical government positions differ across national and sub-national jurisdictions in Canada, the United Kingdom, and Australia?**

By systematically collecting and standardizing job posting data, this research enables analysis of:

- **Position Classification Systems**: How different governments categorize and structure technical roles
- **Compensation Structures**: Salary ranges, pay bands, and benefits for equivalent positions
- **Qualification Requirements**: Educational credentials versus practical experience emphasis
- **Job Descriptions**: Responsibilities, reporting structures, and role definitions
- **Labor Market Dynamics**: Posting frequency, hiring patterns, and demand trends

---

## Current Coverage

### Active Data Collection (Canada)

The project currently collects data from seven Canadian jurisdictions:

| Jurisdiction | Status | Jobs Collected |
|-------------|--------|----------------|
| Government of Canada (Federal) | Active | 27 positions |
| Manitoba | Active | 28 positions |
| Alberta | Active | 27 positions |
| Saskatchewan | Active | 23 positions |
| Ontario | Active | 21 positions |
| British Columbia | Active | 18 positions |
| Nova Scotia | Active | 14 positions |

**Total Canadian Dataset**: 158 relevant technical government positions

*Note: These numbers represent jobs that passed the intelligent matching filter (80+ relevance score). The system reviews significantly more postings but retains only those genuinely matching technical job categories.*

## How It Works

### Intelligent Title Matching

Rather than capturing every job posting that mentions technical terms in passing, the system uses **intelligent text matching algorithms** to evaluate job title relevance. This approach significantly reduces false positives and ensures data quality.

**Matching Criteria**:
- **High Match (90-100 points)**: Direct title matches (e.g., "Senior Data Analyst" matches "Data Analyst")
- **Moderate Match (80-89 points)**: Related roles (e.g., "Business Intelligence Analyst" matches "Data Analyst")
- **Filtered Out (Below 80 points)**: Unrelated positions excluded from dataset

**Example Results**:
- ✓ "Senior Data Analyst" (100 points) → Included
- ✓ "Project Data Analyst" (100 points) → Included
- ✗ "Wildlife Biologist" (0 points) → Excluded
- ✗ "Administrative Assistant" (0 points) → Excluded

This filtering reduces irrelevant results by 80-95%, ensuring the dataset contains only genuinely technical positions.

### Data Collection Workflow

1. **Automated Navigation**: An automated browsing tool visits official government job boards
2. **Intelligent Filtering**: Text matching algorithms evaluate title relevance against 44 predefined job categories
3. **Structured Data Extraction**: Job details are parsed into standardized format for analysis
4. **Database Storage**: Validated data is uploaded to a PostgreSQL database for querying and research

---

## Data Fields Collected

Each job posting in the dataset includes comprehensive information to support comparative analysis:

**Core Identification**:
- Job title, classification level, and requisition number
- Ministry/department and geographic location
- Posting and closing dates

**Compensation Details**:
- Annual salary ranges
- Bi-weekly pay information (where applicable)
- Benefits and compensation notes

**Position Requirements**:
- Required qualifications and credentials
- Experience requirements
- Skills and competencies

**Additional Information**:
- Full job description and responsibilities
- Application instructions and contact details
- Relevance matching score and collection metadata

---

## Research Applications

This dataset supports multiple research directions in comparative public administration:

**Cross-Jurisdictional Comparison**:
- How do different governments structure equivalent technical roles?
- What are the salary differentials for similar positions across jurisdictions?

**Labor Market Analysis**:
- Which technical skills are in highest demand across government sectors?
- How do posting frequencies vary by jurisdiction and role type?

**Policy Research**:
- What qualification requirements do governments emphasize (education vs. experience)?
- How do job descriptions reflect different governance approaches?

**Workforce Planning**:
- What are the geographic distributions of technical opportunities?
- How do hiring patterns differ between federal and provincial/state levels?

---

## Sample Data Output

After collection, data is organized in structured format for analysis. Example job record (British Columbia):

```json
{
  "job_title": "Senior Data Analyst",
  "ministry": "Ministry of Health",
  "location": "Victoria, BC",
  "salary": "$74,000 - $97,000 per year",
  "closing_date": "2025-11-30",
  "match_score": 100,
  "job_url": "https://..."
}
```

Data is stored in both JSON format for flexibility and PostgreSQL database for efficient querying.

---

## Project Structure

```
public_jobs_scraper/
│
├── list-of-jobs.txt              ← 44 technical job categories monitored
├── requirements.txt              ← Software dependencies
├── README.md                     ← Project documentation
│
├── src/                          ← Data collection modules
│   ├── main.py                   ← Batch runner for all scrapers
│   ├── GOC/                      ← Government of Canada (Federal)
│   ├── BC/                       ← British Columbia
│   ├── AB/                       ← Alberta
│   ├── SAS/                      ← Saskatchewan
│   ├── MAN/                      ← Manitoba
│   ├── ONT/                      ← Ontario
│   ├── NS/                       ← Nova Scotia
│   └── [UK, AUS]/                ← International modules
│
├── data/                         ← Generated job data (local only, not in git)
│   ├── BC/jobs_json/
│   ├── AB/jobs_json/
│   └── [other jurisdictions]/
│
└── logs/                         ← Collection activity logs (local only, not in git)
```

*Note: `data/` and `logs/` directories are excluded from version control as they contain generated output.*

---

## Technology Infrastructure

The project uses research-grade tools to ensure data quality and reproducibility:

- **Playwright**: Automated browsing tool for systematic data collection
- **FuzzyWuzzy**: Text similarity algorithms for intelligent matching
- **PostgreSQL/Supabase**: Relational database for structured data storage
- **Python 3.8+**: Core programming language with scientific computing libraries
- **BeautifulSoup**: HTML parsing for data extraction

---

## Performance Metrics

### Collection Efficiency (Alberta Case Study)

Recent data collection from Alberta demonstrated system effectiveness:
- **Total Positions Reviewed**: 144 postings across 44 job categories
- **Relevant Matches Retained**: 27 positions (18.8% match rate)
- **Collection Time**: Approximately 15 minutes
- **Data Completeness**: 95%+ of fields successfully captured

### Coverage by Jurisdiction

| Jurisdiction | Positions per Category | Match Accuracy | Collection Time |
|-------------|----------------------|----------------|-----------------|
| Federal (GOC) | ~10-15 | 25-35% | ~10 minutes |
| British Columbia | ~30-50 | 20-30% | ~20 minutes |
| Alberta | ~20-30 | 15-25% | ~15 minutes |
| Ontario | ~10-20 | 25-35% | ~10 minutes |
| Manitoba | ~5-10 | 30-40% | ~5 minutes |
| Nova Scotia | ~10-15 | 20-30% | ~10 minutes |

Match rates vary by jurisdiction based on job board structure and posting specificity. Lower match rates indicate more aggressive filtering, ensuring higher data quality.

---

## Next Steps

### Near-Term Development

**United Kingdom Integration**:
- Adapt collection system for UK Civil Service job boards
- Map UK classification systems to Canadian equivalents
- Establish baseline dataset of UK government technical positions

**Australia Integration**:
- Develop collection modules for Australian Public Service (APS)
- Integrate state-level job boards (New South Wales, Victoria, Queensland)
- Standardize Australian classification frameworks with Canadian/UK systems

### Medium-Term Research Goals (2026)

**Comparative Analysis Dashboard**:
- Interactive visualization of cross-jurisdictional comparisons
- Salary benchmarking tools for equivalent positions
- Geographic distribution mapping

**Longitudinal Tracking**:
- Monthly data collection to identify hiring trends
- Seasonal pattern analysis
- Demand forecasting for technical skills

**Advanced Analytics**:
- Natural language processing of job descriptions
- Skill requirement clustering analysis
- Qualification pathway mapping

### Long-Term Vision

**Publication and Dissemination**:
- Academic papers on comparative public sector labor markets
- Policy briefs for government HR departments
- Public dataset release for researchers

**Expansion**:
- Additional Canadian provinces (Quebec, Saskatchewan, etc.)
- Additional countries (New Zealand, other Westminster systems)
- Private sector comparison module

---

## Acknowledgments

**Research Context**: Developed for comparative public administration research examining technical workforce structures across Westminster-style governance systems.

**Technology Stack**: Built using open-source research tools including Playwright (automated browsing), PostgreSQL (data storage), and Python scientific computing libraries.

**Data Sources**: All data collected from publicly accessible government job boards in compliance with standard web access protocols.

---

## License

This project is developed for educational and research purposes. Data collection respects website terms of service and is limited to publicly available information. The resulting dataset is intended for academic research and policy analysis.

---

*Last updated: November 9, 2025*
