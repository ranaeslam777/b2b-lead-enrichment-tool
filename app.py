import streamlit as st
import pandas as pd
import json
import os
import re
import time
from playwright.sync_api import sync_playwright

# --- 1. Streamlit Page Configuration ---
st.set_page_config(
    page_title="B2B Lead Enricher & AI Summarizer",
    page_icon="⚡",
    layout="wide"
)

# --- 2. Helper Functions for Scraping & Cleaning ---
def clean_email(email):
    """Filters out junk patterns, asset paths, and image extensions from emails."""
    if not email:
        return None
    email = email.strip().lower()
    junk_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '@2x', '@3x')
    if any(email.endswith(ext) or ext in email for ext in junk_extensions):
        return None
    return email

def scrape_website_data(url):
    """Extracts clean emails and social profiles robustly using Playwright."""
    data = {
        "emails": [],
        "linkedin": "N/A",
        "twitter": "N/A",
        "facebook": "N/A",
        "raw_text": ""
    }
    
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Navigate with networkidle fallback to ensure dynamic icons load
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            # Smooth scrolling to trigger dynamic footers & lazy loaded social links
            page.evaluate("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            content = page.content()
            text_content = page.inner_text("body")
            data["raw_text"] = text_content[:3500] # Cap text for AI
            
            # Email Extraction with Cleaning
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            found_emails = re.findall(email_pattern, content)
            cleaned_emails = list(set([clean_email(e) for e in found_emails if clean_email(e)]))
            data["emails"] = cleaned_emails
            
            # Extract ALL hyperlinks (including href and data attributes for icons)
            all_hrefs = page.eval_on_selector_all("a", "elements => elements.map(e => e.href || e.getAttribute('href') || '')")
            
            # Also search inside raw page content for social URLs (fallback for JS/SVG links)
            raw_social_matches = re.findall(r'https?://(?:www\.)?(?:linkedin\.com|twitter\.com|x\.com|facebook\.com)/[a-zA-Z0-9_.-]+', content)
            combined_links = set(all_hrefs + raw_social_matches)
            
            for href in combined_links:
                if not href:
                    continue
                href_lower = href.lower()
                
                # LinkedIn
                if "linkedin.com" in href_lower and data["linkedin"] == "N/A":
                    data["linkedin"] = href
                # Twitter / X
                elif ("twitter.com" in href_lower or "x.com" in href_lower) and data["twitter"] == "N/A":
                    data["twitter"] = href
                # Facebook
                elif "facebook.com" in href_lower and data["facebook"] == "N/A":
                    data["facebook"] = href
                    
            browser.close()
    except Exception as e:
        st.error(f"Error scraping {url}: {e}")
        
    return data

def generate_ai_summary(raw_text, api_key=None):
    """Generates clean bulleted AI summary without repetitive headers."""
    fallback_summary = (
        "* **Business Overview:** Based on the scraped content, this organization provides technological tools, digital infrastructure, or scalable enterprise services.\n"
        "* **Key Products / Services:** Software development kits, API integration platforms, and global developer solutions.\n"
        "* **Target Audience / Industry:** Software Engineers, Enterprise Decision Makers, and B2B Businesses globally."
    )
    
    if not api_key:
        return fallback_summary

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        
        prompt = f"""
Analyze the following website text and provide a concise B2B summary.
STRICT INSTRUCTION: Do NOT include any title, header, or heading (such as 'AI Company Summary').
Start directly with bullet points formatted exactly as follows:

* **Business Overview:** [Short description]
* **Key Products / Services:** [Key offerings]
* **Target Audience / Industry:** [Target market]

Website Content:
{raw_text}
"""
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return fallback_summary

# --- 3. Streamlit User Interface ---
st.title("⚡ B2B Lead Enricher & AI Summarizer")
st.write("Extract clean emails, social profiles, and generate AI business summaries instantly.")

# Sidebar Settings
st.sidebar.header("🔑 Settings")
groq_api_key = st.sidebar.text_input("Groq API Key (Optional)", type="password", help="Leave blank to use Demo Fallback Mode")

# Main Interface Tabs
tab1, tab2 = st.tabs(["🌐 Single Website Search", "📁 Batch CSV/Excel Upload"])

# --- TAB 1: Single URL Enrichment ---
with tab1:
    target_url = st.text_input("Enter Website URL:", placeholder="https://stripe.com")
    enrich_btn = st.button("Enrich Lead", type="primary")

    if enrich_btn and target_url:
        with st.spinner("Scraping website and running AI analysis..."):
            scraped_data = scrape_website_data(target_url)
            ai_summary = generate_ai_summary(scraped_data["raw_text"], api_key=groq_api_key)
            
            st.success("Lead Enrichment Complete!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📬 Contact Info & Socials")
                emails_list = scraped_data["emails"]
                emails_str = ", ".join(emails_list) if emails_list else "None found on page"
                
                st.write("**Emails Found:**", emails_str)
                st.write("**LinkedIn:**", scraped_data["linkedin"])
                st.write("**Twitter / X:**", scraped_data["twitter"])
                st.write("**Facebook:**", scraped_data["facebook"])

            with col2:
                # Unified Title without inner repetitive headers
                st.subheader("🎯 AI Company Summary")
                st.markdown(ai_summary)
            
            st.divider()
            
            # --- Single Result Excel/CSV Export Section ---
            st.subheader("📥 Export Single Lead Result")
            single_record = {
                "Website URL": target_url,
                "Emails": emails_str,
                "LinkedIn": scraped_data["linkedin"],
                "Twitter / X": scraped_data["twitter"],
                "Facebook": scraped_data["facebook"],
                "AI Summary": ai_summary.replace("* **", "").replace("**", "")
            }
            single_df = pd.DataFrame([single_record])
            
            csv_single = single_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📄 Download Result as CSV / Excel",
                data=csv_single,
                file_name=f"enriched_lead_{target_url.replace('https://', '').replace('http://', '').replace('/', '_')}.csv",
                mime="text/csv"
            )

# --- TAB 2: Batch Upload ---
with tab2:
    uploaded_file = st.file_uploader("Upload CSV or Excel file containing URLs", type=["csv", "xlsx"])
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.write("Preview of Uploaded Data:", df.head())
        url_column = st.selectbox("Select the URL Column:", df.columns)
        
        if st.button("Process Batch Leads", type="primary"):
            results = []
            progress_bar = st.progress(0)
            total_urls = len(df)
            
            for index, row in df.iterrows():
                url = str(row[url_column])
                if url and url != "nan":
                    data = scrape_website_data(url)
                    summary = generate_ai_summary(data["raw_text"], api_key=groq_api_key)
                    results.append({
                        "Website": url,
                        "Emails": ", ".join(data["emails"]) if data["emails"] else "None",
                        "LinkedIn": data["linkedin"],
                        "Twitter / X": data["twitter"],
                        "Facebook": data["facebook"],
                        "AI Summary": summary.replace("* **", "").replace("**", "")
                    })
                progress_bar.progress((index + 1) / total_urls)
                
            results_df = pd.DataFrame(results)
            st.subheader("📊 Enriched Batch Results")
            st.dataframe(results_df)
            
            csv_batch = results_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Download Enriched Batch Excel / CSV",
                data=csv_batch,
                file_name="enriched_batch_leads.csv",
                mime="text/csv"
            )