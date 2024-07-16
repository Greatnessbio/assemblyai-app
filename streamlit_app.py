import streamlit as st
import requests
import json
import time
import base64
from streamlit.logger import get_logger

try:
    from exa_py import Exa
    exa_available = True
except ImportError:
    exa_available = False
    st.warning("Exa package is not installed. Exa search functionality will be disabled.")

LOGGER = get_logger(__name__)

# ... (keep the existing functions)

def generate_search_query(question, openrouter_api_key):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "anthropic/claude-3-sonnet-20240229",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that generates search queries based on user questions. Only generate one search query."},
            {"role": "user", "content": question}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.RequestException as e:
        LOGGER.error(f"OpenRouter API request failed: {e}")
    return None

def get_exa_news_results(query, exa_api_key):
    if not exa_available:
        return None
    exa = Exa(api_key=exa_api_key)
    try:
        search_response = exa.search(
            query,
            use_autoprompt=True,
            type="neural",
            num_results=10
        )
        return search_response.results
    except Exception as e:
        LOGGER.error(f"Exa news search request failed: {e}")
    return None

def get_linkedin_company_insights(company_url, rapidapi_key):
    url = "https://linkedin-data-api.p.rapidapi.com/get-company-insights"
    querystring = {"username": company_url.split("/")[-2]}  # Extract company name from URL
    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        LOGGER.error(f"LinkedIn company insights request failed: {e}")
    return None

def get_linkedin_company_posts(company_url, rapidapi_key):
    url = "https://linkedin-data-api.p.rapidapi.com/get-company-posts"
    querystring = {"username": company_url.split("/")[-2], "start": "0"}
    headers = {
        "x-rapidapi-key": rapidapi_key,
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        LOGGER.error(f"LinkedIn company posts request failed: {e}")
    return None

def analyze_linkedin_posts(context, openrouter_api_key):
    prompt = """
    Analyze the company's LinkedIn posts based on the provided data:
    1. Posting frequency and consistency
    2. Types of content shared (e.g., company news, industry insights, product information)
    3. Use of media (images, videos, links) in posts
    4. Engagement metrics (likes, comments, shares) and trends
    5. Use of hashtags and mentions
    6. Tone and style of writing in posts
    7. Any recurring themes or campaigns
    8. Notable recent announcements or updates
    
    Provide a summary of the company's content strategy on LinkedIn, including strengths and areas for improvement.
    """
    return process_with_openrouter(prompt, context, openrouter_api_key)

def main_app():
    st.title("Comprehensive Company Analyst")

    api_keys = load_api_keys()
    if not api_keys:
        return

    company_url = st.text_input("Enter the company's website URL:")
    linkedin_url = st.text_input("Enter the company's LinkedIn URL:")

    if st.button("Analyze Company") and company_url and linkedin_url:
        with st.spinner("Analyzing... This may take a few minutes."):
            # Fetch data
            jina_results = get_jina_search_results(company_url, api_keys["jina"])
            exa_results = get_exa_search_results(company_url, api_keys["exa"]) if exa_available else None
            linkedin_data = get_linkedin_company_data(linkedin_url, api_keys["rapidapi"])
            linkedin_posts = get_linkedin_company_posts(linkedin_url, api_keys["rapidapi"])
            linkedin_insights = get_linkedin_company_insights(linkedin_url, api_keys["rapidapi"])
            
            # Generate and perform news search
            news_query = generate_search_query(f"Latest news about {company_url}", api_keys["openrouter"])
            news_results = get_exa_news_results(news_query, api_keys["exa"]) if exa_available else None

            # Store raw data in session state
            st.session_state.jina_results = jina_results
            st.session_state.exa_results = exa_results
            st.session_state.linkedin_data = linkedin_data
            st.session_state.linkedin_posts = linkedin_posts
            st.session_state.linkedin_insights = linkedin_insights
            st.session_state.news_results = news_results

            # Prepare context for analysis
            context = {
                "jina_results": jina_results,
                "exa_results": [result.__dict__ for result in exa_results] if exa_results else None,
                "linkedin_data": linkedin_data,
                "linkedin_posts": linkedin_posts,
                "linkedin_insights": linkedin_insights,
                "news_results": [result.__dict__ for result in news_results] if news_results else None
            }

            # Perform analyses
            company_info = analyze_company_info(context, api_keys["openrouter"])
            competitor_analysis = analyze_competitors(context, api_keys["openrouter"])
            linkedin_profile_analysis = analyze_linkedin_profile(context, api_keys["openrouter"])
            linkedin_posts_analysis = analyze_linkedin_posts(context, api_keys["openrouter"])

            # Store analyses in session state
            st.session_state.company_info = company_info
            st.session_state.competitor_analysis = competitor_analysis
            st.session_state.linkedin_profile_analysis = linkedin_profile_analysis
            st.session_state.linkedin_posts_analysis = linkedin_posts_analysis

            # Generate executive summary
            analyses = {
                "company_info": company_info,
                "competitor_analysis": competitor_analysis,
                "linkedin_profile_analysis": linkedin_profile_analysis,
                "linkedin_posts_analysis": linkedin_posts_analysis
            }
            executive_summary = generate_executive_summary(analyses, api_keys["openrouter"])
            st.session_state.executive_summary = executive_summary

            # Compile full report
            full_report = f"""# Comprehensive Company Analysis

## Executive Summary

{executive_summary}

## Detailed Company Information

{company_info}

## Competitor Analysis

{competitor_analysis}

## LinkedIn Profile Analysis

{linkedin_profile_analysis}

## LinkedIn Posts Analysis

{linkedin_posts_analysis}
"""
            st.session_state.full_report = full_report

            st.success("Analysis completed!")

    if 'full_report' in st.session_state:
        st.markdown(st.session_state.full_report)

        # Provide download link for the full report
        report_filename = "comprehensive_company_analysis.md"
        download_link = get_download_link(st.session_state.full_report, report_filename, "Download Full Report")
        st.markdown(download_link, unsafe_allow_html=True)

        # Display raw data in expanders
        if st.session_state.get('jina_results'):
            with st.expander("Raw Jina Search Results"):
                st.json(st.session_state.jina_results)
        
        if st.session_state.get('exa_results'):
            with st.expander("Raw Exa Search Results"):
                st.json([result.__dict__ for result in st.session_state.exa_results])

        if st.session_state.get('linkedin_data'):
            with st.expander("Raw LinkedIn Company Data"):
                st.json(st.session_state.linkedin_data)

        if st.session_state.get('linkedin_posts'):
            with st.expander("Raw LinkedIn Company Posts"):
                st.json(st.session_state.linkedin_posts)

        if st.session_state.get('linkedin_insights'):
            with st.expander("Raw LinkedIn Company Insights"):
                st.json(st.session_state.linkedin_insights)

        if st.session_state.get('news_results'):
            with st.expander("Raw News Search Results"):
                st.json([result.__dict__ for result in st.session_state.news_results])

# ... (keep the login_page and display functions)

if __name__ == "__main__":
    display()
