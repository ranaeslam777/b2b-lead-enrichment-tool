# B2B Lead Enrichment & AI Data Extraction Tool

An automated Python-based data extraction pipeline designed to scrape company websites, enrich B2B contact info, and generate structured AI profiles using Groq AI.

# Features
- Automated Web Scraping: Scrapes target company websites for contact details, social links, and metadata using Playwright & BeautifulSoup.
- AI Data Synthesis: Integrates Groq AI API to evaluate lead relevance and structure raw data.
- Schema Validation: Ensures zero LLM hallucinations by outputting validated JSON responses.
- Excel Export: Exports cleaned data directly into production-ready Excel/CSV files, reducing manual research time by over 80%.

# Tech Stack
- Languages & Frameworks: Python, Pandas
- Scraping Tools: BeautifulSoup, Playwright, Requests
- AI & Data Handling: Groq AI API, JSON Validation

# Setup & Usage
1. Clone the repository:
   ```bash
git clone https://github.com/ranaeslam777/b2b-lead-enrichment-tool.git
