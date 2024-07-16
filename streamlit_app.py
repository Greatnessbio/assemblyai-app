import streamlit as st
import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Check for API keys
if 'api_keys' not in st.secrets:
    st.error("API keys are missing from the secrets file.")
    st.stop()

if 'exa' not in st.secrets['api_keys'] or 'openrouter' not in st.secrets['api_keys']:
    st.error("One or more API keys are missing from the secrets file.")
    st.stop()

# ... (keep the login, exa_api_call, get_content, and openrouter_api_call functions as they are)

def main_app():
    try:
        st.title("Competitor Analysis App")
        
        # Input fields for company URLs
        linkedin_url = st.text_input("Enter LinkedIn Company URL")
        company_site = st.text_input("Enter Company Website URL")
        
        if st.button("Analyze"):
            if not linkedin_url or not company_site:
                st.error("Please enter both LinkedIn and company website URLs.")
                return

            with st.spinner("Retrieving content..."):
                linkedin_content = get_content(linkedin_url)
                company_content = get_content(company_site)
            
            if linkedin_content and company_content:
                st.success("Content retrieved successfully!")
                st.write("LinkedIn content preview:", linkedin_content[:500])
                st.write("Company website content preview:", company_content[:500])
                
                with st.spinner("Performing competitor analysis..."):
                    prompt = f"""
                    Perform a competitor analysis based on the following information:
                    
                    LinkedIn content:
                    {linkedin_content}
                    
                    Company website content:
                    {company_content}
                    
                    Provide insights on:
                    1. Company overview
                    2. Products or services
                    3. Target market
                    4. Competitive advantages
                    5. SWOT analysis
                    """
                    
                    try:
                        analysis_result = openrouter_api_call(prompt)
                        st.success("Analysis complete!")
                        st.write("Analysis result:", analysis_result['choices'][0]['message']['content'])
                    except Exception as e:
                        logging.error(f"Error performing analysis: {str(e)}")
                        st.error(f"Error performing analysis. Please check the logs for more details.")
                
                with st.spinner("Finding similar companies..."):
                    similar_data = {
                        "url": linkedin_url,
                        "numResults": 5
                    }
                    try:
                        similar_companies = exa_api_call("findSimilar", similar_data)
                        st.success("Similar companies found!")
                        st.write("Similar companies:")
                        for company in similar_companies.get('results', []):
                            st.write(f"- {company.get('title', 'Untitled')}: {company.get('url', 'No URL')}")
                    except Exception as e:
                        logging.error(f"Error finding similar companies: {str(e)}")
                        st.error(f"Error finding similar companies. Please check the logs for more details.")
            else:
                st.error("Failed to retrieve content for one or both URLs. Please check the URLs and try again.")
    except Exception as e:
        logging.error(f"Unexpected error in main_app: {str(e)}")
        st.error("An unexpected error occurred. Please check the logs for more details.")

# Main app logic
try:
    if not st.session_state.logged_in:
        login()
    else:
        main_app()
except Exception as e:
    logging.error(f"Unexpected error in main app logic: {str(e)}")
    st.error("An unexpected error occurred. Please check the logs for more details.")
