import streamlit as st
import requests
import json

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login():
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if (username == st.secrets["credentials"]["username"] and 
            password == st.secrets["credentials"]["password"]):
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

def exa_api_call(endpoint, data):
    url = f"https://api.exa.ai/{endpoint}"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": st.secrets['api_keys']['exa']
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def get_content(url):
    # First, search for the URL
    search_data = {
        "query": f"url:{url}",
        "numResults": 1,
        "useAutoprompt": False
    }
    search_result = exa_api_call("search", search_data)
    
    if not search_result['results']:
        return None

    # Then, get the content using the ID from the search result
    content_data = {
        "ids": [search_result['results'][0]['id']],
        "text": {}
    }
    content_result = exa_api_call("contents", content_data)
    
    if content_result and content_result[0]['text']:
        return content_result[0]['text']['text']
    return None

def openrouter_api_call(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {st.secrets['api_keys']['openrouter']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def main_app():
    st.title("Competitor Analysis App")
    
    # Input fields for company URLs
    linkedin_url = st.text_input("Enter LinkedIn Company URL")
    company_site = st.text_input("Enter Company Website URL")
    
    if st.button("Analyze"):
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
                
                analysis_result = openrouter_api_call(prompt)
            
            st.success("Analysis complete!")
            st.write("Analysis result:", analysis_result['choices'][0]['message']['content'])
            
            with st.spinner("Finding similar companies..."):
                similar_data = {
                    "url": linkedin_url,
                    "numResults": 5
                }
                similar_companies = exa_api_call("findSimilar", similar_data)
            
            st.success("Similar companies found!")
            st.write("Similar companies:")
            for company in similar_companies['results']:
                st.write(f"- {company['title']}: {company['url']}")
        else:
            st.error("Failed to retrieve content for one or both URLs. Please check the URLs and try again.")

# Main app logic
if not st.session_state.logged_in:
    login()
else:
    main_app()
