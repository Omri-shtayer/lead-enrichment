import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import io
import csv
from countries import COUNTRIES
import re
import json
import base64
import os
import zipfile

def get_default_dates():
    """Get default start date (4 months ago) and end date (2 months ago)"""
    today = datetime.now()
    start_date = (today - relativedelta(months=4)).replace(day=1)
    end_date = (today - relativedelta(months=2)).replace(day=1)
    return start_date.strftime('%Y-%m'), end_date.strftime('%Y-%m')

def validate_date_format(date_str):
    """Validate that the date is in YYYY-MM format."""
    try:
        if not re.match(r'^\d{4}-(?:0[1-9]|1[0-2])$', date_str):
            return False
        datetime.strptime(date_str, '%Y-%m')
        return True
    except ValueError:
        return False

def format_date(date_str):
    """Format date string to YYYY-MM format."""
    try:
        date = datetime.strptime(date_str, '%Y-%m')
        return date.strftime('%Y-%m')
    except ValueError:
        return None

def get_date_range(start_date, end_date):
    """Generate a list of dates between start_date and end_date in YYYY-MM format."""
    dates = []
    current_date = datetime.strptime(start_date, '%Y-%m')
    end = datetime.strptime(end_date, '%Y-%m')
    
    while current_date <= end:
        dates.append(current_date.strftime('%Y-%m'))
        current_date = current_date + relativedelta(months=1)
    return dates

def parse_metadata(response_data, domain):
    """Parse the static metadata from the API response."""
    return {
        'domain': domain,
        'global_rank': response_data.get('global_rank', ''),
        'category_rank': response_data.get('category_rank', ''),
        'company_name': response_data.get('company_name', ''),
        'site_type': response_data.get('site_type', ''),
        'site_type_new': response_data.get('site_type_new', ''),
        'employee_range': response_data.get('employee_range', ''),
        'estimated_revenue_in_usd': response_data.get('estimated_revenue_in_usd', ''),
        'online_revenue_range': response_data.get('online_revenue_range', ''),
        'headquarters': response_data.get('headquarters', ''),
        'website_category': response_data.get('website_category', ''),
        'website_category_new': response_data.get('website_category_new', ''),
        'zip_code': response_data.get('zip_code', '')
    }

def parse_time_series(response_data, domain, date):
    """Parse time series metrics for a specific date."""
    metrics = {
        'domain': domain,
        'date': date
    }
    
    def get_metric_value(metric_array, target_date):
        if not isinstance(metric_array, list):
            return ''
        for entry in metric_array:
            if isinstance(entry, dict) and entry.get('date') == target_date:
                return entry.get('value')
        return ''

    # Basic metrics
    metrics['visits'] = str(get_metric_value(response_data.get('visits', []), date) or '')
    metrics['unique_visitors'] = str(get_metric_value(response_data.get('unique_visitors', []), date) or '')
    metrics['bounce_rate'] = str(get_metric_value(response_data.get('bounce_rate', []), date) or '')
    metrics['pages_per_visit'] = str(get_metric_value(response_data.get('pages_per_visit', []), date) or '')
    metrics['average_visit_duration'] = str(get_metric_value(response_data.get('average_visit_duration', []), date) or '')
    metrics['mom_growth'] = str(get_metric_value(response_data.get('mom_growth', []), date) or '')

    # Mobile/Desktop share
    mobile_desktop = get_metric_value(response_data.get('mobile_desktop_share', []), date)
    if isinstance(mobile_desktop, dict):
        metrics['desktop_share'] = str(mobile_desktop.get('desktop_share', ''))
        metrics['mobile_share'] = str(mobile_desktop.get('mobile_share', ''))
    else:
        metrics['desktop_share'] = ''
        metrics['mobile_share'] = ''

    # Traffic Sources
    traffic_sources = get_metric_value(response_data.get('traffic_sources', []), date)
    if isinstance(traffic_sources, list):
        for source in traffic_sources:
            if isinstance(source, dict):
                source_type = source.get('source_type', '').lower().replace(' ', '_')
                share = source.get('share', '')
                if source_type:
                    metrics[f'traffic_{source_type}'] = str(share) if share != '' else ''

    # Geography Share - Using numbered columns (1-10)
    geography_share = get_metric_value(response_data.get('geography_share', []), date)
    if isinstance(geography_share, list):
        # Initialize all geo columns with empty values
        for i in range(1, 11):
            metrics[f'geo_country_{i}'] = ''
            metrics[f'geo_country_share_{i}'] = ''
        
        # Fill in available data
        for i, country in enumerate(geography_share[:10], 1):  # Only process top 10 countries
            if isinstance(country, dict):
                metrics[f'geo_country_{i}'] = str(country.get('country', ''))
                metrics[f'geo_country_share_{i}'] = str(country.get('share', ''))

    return metrics

def fetch_lead_data(domain, api_key, start_date, end_date, country):
    """Fetch lead enrichment data for a single domain."""
    if not all([validate_date_format(start_date), validate_date_format(end_date)]):
        return {
            'metadata': [{
                'domain': domain,
                'error': 'Invalid date format. Please use YYYY-MM format.'
            }],
            'time_series': []
        }

    url = f"https://api.similarweb.com/v1/website/{domain}/lead-enrichment/all"
    params = {
        "api_key": api_key,
        "start_date": f"{start_date}-01",
        "end_date": f"{end_date}-01",
        "country": country,
        "main_domain_only": "false",
        "format": "json",
        "show_verified": "false"
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            metadata = parse_metadata(data, domain)
            time_series = []
            dates = get_date_range(start_date, end_date)
            for date in dates:
                formatted_date = f"{date}-01"
                time_series_entry = parse_time_series(data, domain, formatted_date)
                time_series.append(time_series_entry)
            
            return {
                'metadata': [metadata],
                'time_series': time_series
            }
        elif response.status_code == 403:
            error_message = "API authentication failed. Please check your API key and try again."
            try:
                error_data = response.json()
                if error_data.get('meta', {}).get('error_message'):
                    error_message = error_data['meta']['error_message']
            except:
                pass
            return {
                'metadata': [{
                    'domain': domain,
                    'error': error_message
                }],
                'time_series': []
            }
        else:
            error_message = "Unknown error occurred"
            try:
                error_data = response.json()
                if error_data.get('meta', {}).get('error_message'):
                    error_message = error_data['meta']['error_message']
            except:
                error_message = response.text if response.text else f"HTTP Error {response.status_code}"
            
            return {
                'metadata': [{
                    'domain': domain,
                    'error': error_message
                }],
                'time_series': []
            }
    except requests.exceptions.RequestException as e:
        return {
            'metadata': [{
                'domain': domain,
                'error': f"Network error: {str(e)}"
            }],
            'time_series': []
        }
    except Exception as e:
        return {
            'metadata': [{
                'domain': domain,
                'error': f"Error processing data: {str(e)}"
            }],
            'time_series': []
        }

# Custom styling
st.set_page_config(
    page_title="SimilarWeb Lead Enrichment Sample Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with SimilarWeb brand colors
st.markdown("""
    <style>
        :root {
            --sw-primary: #1B2838;
            --sw-secondary: #2D5A88;
            --sw-accent: #4A90E2;
            --sw-light: #E8F0FE;
        }
        
        section[data-testid="stSidebar"] {
            background-color: var(--sw-light);
            padding: 1rem;
        }
        
        section[data-testid="stSidebar"] .stMarkdown {
            color: var(--sw-secondary) !important;
        }
        
        section[data-testid="stSidebar"] .stSubheader {
            color: var(--sw-primary) !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            margin-bottom: 1rem !important;
        }
        
        .stTitle {
            color: var(--sw-accent) !important;
            font-size: 1.5rem !important;
            font-weight: 500 !important;
            margin-bottom: 0 !important;
        }
        
        .subtitle {
            color: var(--sw-secondary);
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        
        .stButton > button {
            background-color: var(--sw-accent) !important;
            color: white !important;
            border: none !important;
            border-radius: 4px !important;
            padding: 0.75rem 1.5rem !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
            width: 100% !important;
        }
        
        .stButton > button:hover {
            background-color: var(--sw-secondary) !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        }
        
        .stTextInput > div > div > input {
            border-radius: 4px !important;
            border-color: #ccc !important;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: var(--sw-accent) !important;
            box-shadow: 0 0 0 1px var(--sw-accent) !important;
        }
        
        .stSelectbox > div > div > div {
            border-radius: 4px !important;
        }
        
        div[data-testid="stLinkButton"] > a {
            background: none !important;
            border: none !important;
            padding: 0 !important;
            color: var(--sw-accent) !important;
            text-decoration: none !important;
            cursor: pointer !important;
            font-size: 0.9rem !important;
        }
        div[data-testid="stLinkButton"] > a:hover {
            color: var(--sw-secondary) !important;
            text-decoration: underline !important;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar - API Configuration
with st.sidebar:
    st.subheader("API Configuration")
    st.markdown("Configure the SimilarWeb Lead Enrichment API parameters")
    
    api_key = st.text_input(
        "API Key", 
        type="password",
        help="Enter your SimilarWeb API key. You can find this in your SimilarWeb account settings."
    )
    
    # Date inputs with default values
    default_start, default_end = get_default_dates()
    start_date = st.text_input(
        "Start Date",
        default_start,
        help="Format: YYYY-MM (e.g., 2024-03). Data is available for up to 12 months before end date."
    )
    if not validate_date_format(start_date):
        st.error("Start date must be in YYYY-MM format (e.g., 2024-03)")

    end_date = st.text_input(
        "End Date",
        default_end,
        help="Format: YYYY-MM (e.g., 2024-03). Should be the last completed month."
    )
    if not validate_date_format(end_date):
        st.error("End date must be in YYYY-MM format (e.g., 2024-03)")

    # Country selection and main domain checkbox
    selected_country = st.selectbox(
        "Country",
        options=COUNTRIES,
        format_func=lambda x: x.split(" - ")[0],
        help="Select the country for which you want to retrieve data."
    )
    country_code = selected_country.split(" - ")[1]
    main_domain_only = st.checkbox(
        "Main Domain Only",
        value=False,
        help="If checked, only the main domain will be analyzed (e.g., 'example.com' instead of 'blog.example.com')."
    )

# Main content
st.title("SimilarWeb Lead Enrichment Sample Generator")
st.markdown("<p class='subtitle'>Generate sample lead enrichment data from SimilarWeb API</p>", unsafe_allow_html=True)

# Add info about data credits
st.info("ℹ️ Each domain processed will cost 25 data credits from your API quota.", icon="ℹ️")

# Domain input section
st.subheader("Enter Domains")
st.markdown("Enter up to 100 domains (one per line) to generate CSV data")

# Initialize session state for domains if not exists
if 'domains_text' not in st.session_state:
    st.session_state.domains_text = ""

# Text area for domains with improved help text
domains_text = st.text_area(
    "Enter domains (one per line)",
    value=st.session_state.domains_text,
    height=150,
    help="Enter domain names without 'http://', 'https://' or 'www.' prefix. Example: amazon.com"
)

# Example domains link with better styling
st.markdown("""
    <style>
        .small-text-button {
            background: none !important;
            color: var(--sw-accent) !important;
            border: none !important;
            padding: 0 !important;
            font-size: 0.9rem !important;
            opacity: 0.9;
            margin-bottom: 1rem !important;
        }
        .small-text-button:hover {
            color: var(--sw-secondary) !important;
            text-decoration: underline !important;
        }
        .small-text-button > div {
            display: inline-flex !important;
            gap: 0.3rem !important;
        }
        
        /* Add progress bar styling */
        .stProgress > div > div > div > div {
            background-color: var(--sw-accent) !important;
        }
        
        /* Style info messages */
        .stAlert {
            background-color: var(--sw-light) !important;
            border-color: var(--sw-accent) !important;
        }
    </style>
""", unsafe_allow_html=True)

# Example domains button styled as text
if st.button("📋 Use example domains", type="secondary", use_container_width=False, key="example_domains"):
    st.session_state.domains_text = """amazon.com
facebook.com
google.com"""
    st.rerun()

# Process button with loading state
if st.button("Generate CSV", type="primary"):
    if not api_key:
        st.error("⚠️ Please enter an API key")
    elif not domains_text:
        st.error("⚠️ Please enter at least one domain")
    elif not validate_date_format(start_date) or not validate_date_format(end_date):
        st.error("⚠️ Please enter valid dates in YYYY-MM format")
    elif datetime.strptime(end_date, '%Y-%m') < datetime.strptime(start_date, '%Y-%m'):
        st.error("⚠️ End date must be after start date")
    else:
        # Process domains from text area
        domains = [d.strip() for d in domains_text.split('\n') if d.strip()]
        
        if len(domains) > 100:
            st.error("⚠️ Maximum 100 domains allowed")
        elif not domains:
            st.error("⚠️ No valid domains found")
        else:
            with st.spinner('🔄 Processing domains... This may take a few minutes.'):
                all_metadata = []
                all_time_series = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                has_errors = False
                for i, domain in enumerate(domains):
                    status_text.text(f"Processing {domain}...")
                    result = fetch_lead_data(domain, api_key, start_date, end_date, country_code)
                    
                    # Check for API errors
                    if result['metadata'][0].get('error'):
                        has_errors = True
                        st.error(f"❌ Error processing {domain}: {result['metadata'][0]['error']}")
                        continue
                    
                    all_metadata.extend(result['metadata'])
                    all_time_series.extend(result['time_series'])
                    progress_bar.progress((i + 1) / len(domains))
                
                if has_errors:
                    status_text.text("⚠️ Processing complete with errors. Check the error messages above.")
                else:
                    status_text.text("✅ Processing complete!")
                
                # Only create DataFrames if we have data
                if all_metadata or all_time_series:
                    # Create DataFrames
                    df_metadata = pd.DataFrame(all_metadata)
                    df_time_series = pd.DataFrame(all_time_series)
                    
                    # Ensure domain and date are first columns in time series
                    if not df_time_series.empty:
                        cols = ['domain', 'date'] + [col for col in df_time_series.columns if col not in ['domain', 'date']]
                        df_time_series = df_time_series[cols]
                    
                    # Show previews with better styling
                    st.subheader("📊 Metadata Preview:")
                    st.dataframe(df_metadata, use_container_width=True)
                    
                    st.subheader("📈 Time Series Preview:")
                    st.dataframe(df_time_series, use_container_width=True)
                    
                    # Download section with better organization
                    st.subheader("📥 Download Options")
                    
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    with col1:
                        csv_buffer_metadata = io.StringIO()
                        df_metadata.to_csv(csv_buffer_metadata, index=False)
                        st.download_button(
                            label="⬇️ Download Metadata CSV",
                            data=csv_buffer_metadata.getvalue(),
                            file_name="similarweb_metadata.csv",
                            mime="text/csv",
                            help="Download the metadata information as a CSV file"
                        )
                    
                    with col2:
                        csv_buffer_time_series = io.StringIO()
                        df_time_series.to_csv(csv_buffer_time_series, index=False)
                        st.download_button(
                            label="⬇️ Download Time Series CSV",
                            data=csv_buffer_time_series.getvalue(),
                            file_name="similarweb_time_series.csv",
                            mime="text/csv",
                            help="Download the time series data as a CSV file"
                        )
                    
                    with col3:
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            metadata_buffer = io.StringIO()
                            df_metadata.to_csv(metadata_buffer, index=False)
                            zip_file.writestr('similarweb_metadata.csv', metadata_buffer.getvalue())
                            
                            time_series_buffer = io.StringIO()
                            df_time_series.to_csv(time_series_buffer, index=False)
                            zip_file.writestr('similarweb_time_series.csv', time_series_buffer.getvalue())
                        
                        st.download_button(
                            label="⬇️ Download All CSVs",
                            data=zip_buffer.getvalue(),
                            file_name="similarweb_data.zip",
                            mime="application/zip",
                            help="Download both Metadata and Time Series CSVs in a zip file"
                        ) 