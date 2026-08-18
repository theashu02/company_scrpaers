# Sequoia Company Scraper & Social Links Pipeline

A production-grade Python scraping pipeline for extracting, deduplicating, and enriching Sequoia Capital portfolio company data across parameterized industry URLs with comprehensive website, career, and social media links.

---

## 📋 Data Collected For Each Company

| Category | Extracted Data Fields |
| :--- | :--- |
| **Identification** | `name`, `slug`, `id`, `description` |
| **Core Links** | `website_url`, `domain`, `careers_url`, `sequoia_jobs_url`, `sequoia_portfolio_url` |
| **Social Links** | `linkedin_url`, `twitter_url`, `github_url`, `facebook_url`, `instagram_url`, `youtube_url`, `all_social_links` |
| **Careers & ATS** | `ats_platform` (Ashby, Greenhouse, Lever, etc.), `total_jobs`, `num_remote_jobs` |
| **Media Links** | `logo_url` (High-res PNG/SVG), `linkedin_logo_url` |
| **Company Details** | `industries`, `markets`, `office_locations`, `stages`, `staff_count`, `email_domains`, `investors` |

---

## 📁 Project Structure

```
company_scraper/
│
├── config/
│   ├── __init__.py
│   └── config.py               # All 77 industries, URLs, timeouts, headers, output paths
│
├── core/
│   ├── __init__.py
│   └── browser.py              # Playwright browser manager, stealth headers, infinite scrolling
│
├── scrapers/
│   ├── __init__.py
│   └── sequoia.py              # Parameterized URL iterator, response interceptor & concurrent social enricher
│
├── transformers/
│   ├── __init__.py
│   └── datatransform.py        # Schema modeling, multi-industry deduplication, JSON & CSV exporters
│
├── data/
│   ├── raw/                    # Raw intercepted JSON payloads (search_companies_raw.json)
│   └── processed/              # Cleaned datasets (sequoia_companies.json & .csv)
│
├── main.py                     # Central CLI execution pipeline
├── requirements.txt            # Project dependencies
└── README.md                   # Documentation
```

---

## 🚀 How to Run

### 1. Run in Visible Browser (Dev / Non-Headless Mode)
Opens a maximized browser window so you can visually watch the scraping, scrolling, and page transitions across all 77 industries:
```powershell
python main.py
# or explicitly:
python main.py --no-headless
```

### 2. Dev Quick Test (First 3 Industries with Visible Browser)
```powershell
python main.py --limit 3 --no-headless
```

### 3. Test Specific Industry in Dev
```powershell
python main.py --industries "AI,Fintech" --no-headless
```

### 2. Run in Background (Headless Mode)
```powershell
python main.py --headless
```

### 3. Run for Specific Selected Industries
```powershell
python main.py --industries "SaaS,Fintech,Enterprise Software,AI"
```

### 4. Run First N Industries (Test Run)
```powershell
python main.py --limit 5
```

### 5. Process & Enrich Existing Local JSON (`dummy.json`)
```powershell
python main.py --mode transform --file dummy.json
```

---

## 📊 Export Outputs
- **Tabular CSV (with all links & socials)**: [`data/processed/sequoia_companies.csv`](file:///c:/Users/ashut/OneDrive/Desktop/company_scrpaer/data/processed/sequoia_companies.csv)
- **Structured JSON (with all links & socials)**: [`data/processed/sequoia_companies.json`](file:///c:/Users/ashut/OneDrive/Desktop/company_scrpaer/data/processed/sequoia_companies.json)
- **Raw Intercepted API Responses**: [`data/raw/search_companies_raw.json`](file:///c:/Users/ashut/OneDrive/Desktop/company_scrpaer/data/raw/search_companies_raw.json)
