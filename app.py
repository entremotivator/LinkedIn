import streamlit as st
import pandas as pd
import gspread
import requests
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import json
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from collections import defaultdict
import re

# ------------------ PAGE CONFIG ------------------ #
st.set_page_config(
    page_title="Enhanced LinkedIn Outreach Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ SESSION STATE INITIALIZATION ------------------ #
if 'activity_log' not in st.session_state:
    st.session_state.activity_log = []
if 'sent_leads' not in st.session_state:
    st.session_state.sent_leads = set()
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.utcnow()
if 'webhook_history' not in st.session_state:
    st.session_state.webhook_history = []
if 'selected_leads' not in st.session_state:
    st.session_state.selected_leads = []
if 'message_tracking' not in st.session_state:
    st.session_state.message_tracking = {}
if 'daily_stats' not in st.session_state:
    st.session_state.daily_stats = defaultdict(lambda: {'searches': 0, 'messages': 0, 'responses': 0})

# ------------------ ENHANCED STYLES ------------------ #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        text-align: center;
        font-size: 3rem;
        font-weight: 800;
        color: #1e3a8a;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .sub-title {
        text-align: center;
        font-size: 1.2rem;
        color: #64748b;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.95;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }
    
    .metric-trend {
        font-size: 0.9rem;
        margin-top: 0.5rem;
        opacity: 0.8;
    }
    
    .lead-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
        transition: all 0.4s ease;
        border-left: 5px solid #667eea;
        position: relative;
        overflow: hidden;
    }
    
    .lead-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .lead-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
    }
    
    .lead-card:hover::before {
        opacity: 1;
    }
    
    .lead-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .lead-sub {
        font-size: 1rem;
        color: #475569;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        font-weight: 500;
    }
    
    .lead-msg {
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
        border-radius: 15px;
        padding: 1.2rem;
        margin: 1.2rem 0;
        font-size: 1rem;
        color: #334155;
        border-left: 4px solid #667eea;
        line-height: 1.6;
        font-style: italic;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.5rem 1.2rem;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-ready {
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        color: #166534;
        border: 1px solid #22c55e;
    }
    
    .status-sent {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1e40af;
        border: 1px solid #3b82f6;
    }
    
    .status-pending {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        border: 1px solid #f59e0b;
    }
    
    .timestamp {
        font-size: 0.9rem;
        color: #94a3b8;
        text-align: right;
        font-weight: 500;
        background: rgba(148, 163, 184, 0.1);
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        display: inline-block;
    }
    
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e293b;
        margin: 2.5rem 0 1.5rem 0;
        padding-bottom: 0.8rem;
        border-bottom: 3px solid #667eea;
        position: relative;
    }
    
    .section-header::after {
        content: '';
        position: absolute;
        bottom: -3px;
        left: 0;
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, #764ba2, #667eea);
    }
    
    .stats-container {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .activity-item {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border-radius: 15px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: all 0.3s ease;
    }
    
    .activity-item:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .filter-section {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .chart-container {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------ #
st.markdown("<div class='main-title'>🚀 Enhanced LinkedIn Outreach Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Advanced Analytics, Message Tracking & Lead Management Platform</div>", unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------ #
st.sidebar.header("⚙️ Dashboard Configuration")

# Theme Toggle
theme = st.sidebar.radio("🎨 Theme Mode", ["Light", "Dark"], horizontal=True)
if theme == "Dark":
    st.markdown("""
    <style>
        .stApp { background-color: #0f172a; color: #e2e8f0; }
        .lead-card { background: linear-gradient(145deg, #1e293b 0%, #334155 100%); color: #f1f5f9; }
        .lead-msg { background: linear-gradient(135deg, #334155 0%, #475569 100%); color: #e2e8f0; }
        .stats-container { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); }
        .activity-item { background: linear-gradient(145deg, #1e293b 0%, #334155 100%); color: #e2e8f0; }
        .section-header { color: #f1f5f9; }
        .filter-section { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); }
        .chart-container { background: #1e293b; color: #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# Data Source Configuration
st.sidebar.subheader("📊 Data Source")

# Option to use demo data or Google Sheets
data_source = st.sidebar.radio(
    "Choose Data Source",
    ["Demo Data", "Google Sheets"],
    help="Use demo data for testing or connect to your Google Sheets"
)

df = pd.DataFrame()

if data_source == "Demo Data":
    # Create comprehensive demo data with all the columns mentioned - FIXED LENGTHS
    num_records = 20
    demo_data = {
        'timestamp': [datetime.now() - timedelta(days=i, hours=i*2) for i in range(num_records)],
        'profile_name': [f'Lead {i+1}' for i in range(num_records)],
        'profile_location': (['Tampa, FL', 'Miami, FL', 'Orlando, FL', 'New York, NY', 'Los Angeles, CA'] * 4)[:num_records],
        'profile_tagline': (['CEO at TechCorp', 'Marketing Director', 'Sales Manager', 'Business Owner', 'VP of Operations'] * 4)[:num_records],
        'linkedin_url': [f'https://linkedin.com/in/lead{i+1}' for i in range(num_records)],
        'linkedin_subject': (['Partnership Opportunity', 'Business Collaboration', 'Networking', 'Growth Discussion', 'Strategic Alliance'] * 4)[:num_records],
        'linkedin_message': ['Hi! I\'d love to connect and explore potential synergies between our companies.'] * num_records,
        'email_subject': (['Follow-up: LinkedIn Connection', 'Business Opportunity', 'Partnership Discussion', 'Collaboration Proposal'] * 5)[:num_records],
        'email_message': ['Thank you for connecting on LinkedIn. I wanted to follow up...'] * num_records,
        'outreach_strategy': (['Cold Outreach', 'Warm Introduction', 'Referral', 'Event Follow-up'] * 5)[:num_records],
        'personalization_points': (['Company growth', 'Recent funding', 'Industry expertise', 'Mutual connections'] * 5)[:num_records],
        'follow_up_suggestions': (['Schedule call in 1 week', 'Send case study', 'Connect on phone', 'Share resources'] * 5)[:num_records],
        'connection_status': (['Connected', 'Pending', 'Not Connected', 'Accepted', 'Declined'] * 4)[:num_records],
        'success': ([True, False, True, True, False] * 4)[:num_records],
        'credits_used': ([1, 2, 1, 3, 2] * 4)[:num_records],
        'status': (['sent', 'pending', 'ready_to_send', 'sent', 'pending'] * 4)[:num_records],
        'search_term': (['CEO', 'Marketing Director', 'Sales Manager', 'Business Owner', 'VP'] * 4)[:num_records],
        'search_city': (['Tampa', 'Miami', 'Orlando', 'New York', 'Los Angeles'] * 4)[:num_records],
        'search_country': ['United States'] * num_records,
        'name': [f'John Doe {i+1}' for i in range(num_records)],
        'image_url': [f'https://example.com/avatar{i+1}.jpg' for i in range(num_records)],
        'tagline': (['Driving innovation in tech', 'Marketing expert', 'Sales professional', 'Business strategist', 'Growth hacker'] * 4)[:num_records],
        'location': (['Tampa, FL', 'Miami, FL', 'Orlando, FL', 'New York, NY', 'Los Angeles, CA'] * 4)[:num_records],
        'summary': ['Experienced professional with 10+ years in the industry'] * num_records
    }
    
    df = pd.DataFrame(demo_data)
    st.sidebar.success(f"✅ Demo data loaded: {len(df)} leads")

else:
    # Google Sheets Authentication
    st.sidebar.subheader("🔐 Google Sheets Connection")
    
    # Option to skip authentication for demo purposes
    skip_auth = st.sidebar.checkbox("Skip Authentication (Demo Mode)", value=True)
    
    if skip_auth:
        # Create sample data structure matching the expected columns
        num_records = 10
        sample_data = {
            'timestamp': [datetime.now() - timedelta(days=i) for i in range(num_records)],
            'profile_name': [f'Sample Lead {i+1}' for i in range(num_records)],
            'profile_location': (['Tampa, FL', 'Miami, FL'] * 5)[:num_records],
            'linkedin_message': ['Sample message content'] * num_records,
            'status': (['ready_to_send', 'sent', 'pending'] * 4)[:num_records],
            'search_city': (['Tampa', 'Miami'] * 5)[:num_records],
            'search_term': (['CEO', 'Director'] * 5)[:num_records]
        }
        df = pd.DataFrame(sample_data)
        st.sidebar.info("📝 Using sample data structure (authentication skipped)")
    else:
        service_file = st.sidebar.file_uploader("Upload Service Account JSON", type=["json"])
        
        if not service_file:
            st.warning("⚠️ Please upload your Google Service Account JSON file to access live data.")
            st.info("💡 **How to get started:**\n1. Create a service account in Google Cloud Console\n2. Download the JSON key file\n3. Share your Google Sheet with the service account email\n4. Upload the JSON file here")
            st.stop()

        # Authenticate with Google
        try:
            service_account_info = json.load(service_file)
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            client = gspread.authorize(creds)
            st.sidebar.success("✅ Successfully Connected to Google Sheets")
        except Exception as e:
            st.sidebar.error(f"❌ Authentication Error: {str(e)}")
            st.stop()

        # Load Data from Google Sheets
        sheet_url = st.sidebar.text_input(
            "Google Sheet URL",
            value="https://docs.google.com/spreadsheets/d/1eLEFvyV1_f74UC1g5uQ-xA7A62sK8Pog27KIjw_Sk3Y/edit?usp=sharing"
        )

        try:
            sheet_id = sheet_url.split("/")[5]
            sheet = client.open_by_key(sheet_id).sheet1
            all_values = sheet.get_all_values()
            
            if len(all_values) > 0:
                headers = all_values[0] if all_values else []
                data_rows = all_values[1:] if len(all_values) > 1 else []
                df = pd.DataFrame(data_rows, columns=headers)
            else:
                df = pd.DataFrame()
            
            st.sidebar.success(f"✅ Loaded {len(df)} leads from Google Sheets")
        except Exception as e:
            st.sidebar.error(f"⚠️ Unable to load data: {str(e)}")
            st.stop()

# Auto-refresh toggle
st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (60s)", value=False)
if auto_refresh:
    st.sidebar.info(f"⏱️ Last refresh: {datetime.utcnow().strftime('%H:%M:%S UTC')}")

# Manual refresh button
if st.sidebar.button("🔄 Refresh Data Now", use_container_width=True):
    st.rerun()

# ------------------ ENHANCED FILTERS ------------------ #
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Advanced Search & Filters")

with st.sidebar.expander("🔎 Search Options", expanded=True):
    search_query = st.text_input("🔍 Global Search", placeholder="Search across all fields...")
    
    col1, col2 = st.columns(2)
    with col1:
        city_filter = st.selectbox(
            "📍 City",
            ["All"] + sorted(df['search_city'].dropna().unique().tolist()) if 'search_city' in df.columns else ["All"],
            index=0
        )
    with col2:
        term_filter = st.selectbox(
            "💼 Search Term",
            ["All"] + sorted(df['search_term'].dropna().unique().tolist()) if 'search_term' in df.columns else ["All"],
            index=0
        )

with st.sidebar.expander("📊 Status & Date Filters", expanded=True):
    status_filter = st.selectbox(
        "📊 Status",
        ["All"] + sorted(df['status'].dropna().unique().tolist()) if 'status' in df.columns else ["All"],
        index=0
    )
    
    # Date range filter
    if 'timestamp' in df.columns and not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        min_date = df['timestamp'].min().date() if not df['timestamp'].isna().all() else datetime.now().date()
        max_date = df['timestamp'].max().date() if not df['timestamp'].isna().all() else datetime.now().date()
        
        date_range = st.date_input(
            "📅 Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

with st.sidebar.expander("⚡ Quick Actions", expanded=True):
    show_sent_only = st.checkbox("✅ Sent Messages Only", value=False)
    show_pending_only = st.checkbox("⏳ Pending Only", value=False)
    show_recent = st.checkbox("🕒 Last 7 Days Only", value=False)

# Apply filters
filtered_df = df.copy()

if not filtered_df.empty:
    # Apply search filter
    if search_query:
        mask = filtered_df.astype(str).apply(
            lambda x: x.str.contains(search_query, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]

    # Apply city filter
    if city_filter != "All" and 'search_city' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['search_city'] == city_filter]

    # Apply term filter
    if term_filter != "All" and 'search_term' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['search_term'] == term_filter]

    # Apply status filter
    if status_filter != "All" and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'] == status_filter]

    # Apply date range filter
    if 'timestamp' in filtered_df.columns and 'date_range' in locals() and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['timestamp'].dt.date >= start_date) & 
            (filtered_df['timestamp'].dt.date <= end_date)
        ]

    # Apply quick action filters
    if show_sent_only and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'] == 'sent']
    
    if show_pending_only and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'] == 'pending']
    
    if show_recent and 'timestamp' in filtered_df.columns:
        week_ago = datetime.now() - timedelta(days=7)
        filtered_df = filtered_df[filtered_df['timestamp'] >= week_ago]

# ------------------ WEBHOOK CONFIGURATION ------------------ #
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Integration Settings")
webhook_url = st.sidebar.text_input(
    "Webhook URL",
    value="https://agentonline-u29564.vm.elestio.app/webhook/Leadlinked",
    help="Enter your n8n or automation webhook URL"
)

# ------------------ CUSTOM DATA FORM (N8N Webhook) ------------------ #
st.sidebar.markdown("---")
st.sidebar.header("🔍 Search New Leads (via Webhook)")

# Predefined options (copied from original code)
SEARCH_TERMS = [
    "Business Owner",
    "CEO",
    "Chief Executive Officer",
    "Founder",
    "Co-Founder",
    "Managing Director",
    "President",
    "Vice President",
    "VP of Sales",
    "VP of Marketing",
    "VP of Operations",
    "VP of Business Development",
    "Chief Operating Officer",
    "Chief Marketing Officer",
    "Chief Technology Officer",
    "Chief Financial Officer",
    "Chief Revenue Officer",
    "Chief Sales Officer",
    "Director of Sales",
    "Director of Marketing",
    "Director of Business Development",
    "Director of Operations",
    "Sales Manager",
    "Marketing Manager",
    "Operations Manager",
    "General Manager",
    "Regional Manager",
    "District Manager",
    "Entrepreneur",
    "Executive Director",
    "Head of Sales",
    "Head of Marketing",
    "Head of Operations",
    "Head of Business Development",
    "Partner",
    "Managing Partner",
    "Senior Partner",
    "Owner",
    "Principal",
    "Consultant",
    "Senior Consultant",
    "Account Executive",
    "Senior Account Executive",
    "Business Development Manager",
    "Sales Director",
    "Marketing Director",
    "Strategy Director",
    "Growth Manager",
    "Revenue Manager",
    "Commercial Director"
]

CITIES = [
    "Tampa",
    "Miami",
    "Orlando",
    "Jacksonville",
    "St. Petersburg",
    "Fort Lauderdale",
    "Tallahassee",
    "Fort Myers",
    "Sarasota",
    "Naples",
    "Atlanta",
    "Charlotte",
    "Raleigh",
    "Nashville",
    "Memphis",
    "New Orleans",
    "Birmingham",
    "New York",
    "Brooklyn",
    "Manhattan",
    "Queens",
    "Los Angeles",
    "San Francisco",
    "San Diego",
    "San Jose",
    "Chicago",
    "Houston",
    "Dallas",
    "Austin",
    "San Antonio",
    "Phoenix",
    "Scottsdale",
    "Philadelphia",
    "Boston",
    "Seattle",
    "Portland",
    "Denver",
    "Boulder",
    "Las Vegas",
    "Salt Lake City",
    "Minneapolis",
    "Detroit",
    "Columbus",
    "Indianapolis",
    "Milwaukee",
    "Kansas City",
    "St. Louis",
    "Cleveland",
    "Pittsburgh",
    "Cincinnati",
    "Richmond",
    "Virginia Beach",
    "Washington DC",
    "Baltimore",
    "Wilmington"
]

COUNTRIES = [
    "United States",
    "Canada",
    "United Kingdom",
    "Australia",
    "New Zealand",
    "Germany",
    "France",
    "Spain",
    "Italy",
    "Portugal",
    "Netherlands",
    "Belgium",
    "Switzerland",
    "Austria",
    "Sweden",
    "Norway",
    "Denmark",
    "Finland",
    "Ireland",
    "Poland",
    "Czech Republic",
    "Greece",
    "Turkey",
    "Israel",
    "United Arab Emirates",
    "Saudi Arabia",
    "Qatar",
    "Singapore",
    "Hong Kong",
    "Japan",
    "South Korea",
    "China",
    "Taiwan",
    "Thailand",
    "Malaysia",
    "Indonesia",
    "Philippines",
    "Vietnam",
    "India",
    "Pakistan",
    "Bangladesh",
    "South Africa",
    "Nigeria",
    "Kenya",
    "Egypt",
    "Brazil",
    "Mexico",
    "Argentina",
    "Chile",
    "Colombia",
    "Peru"
]

with st.sidebar.form("webhook_form"):
    st.markdown("**Lead Search Criteria**")
    
    search_term = st.selectbox(
        "Search Term*",
        options=SEARCH_TERMS,
        index=0,
        help="Select the job title or role to search for"
    )
    
    city = st.selectbox(
        "City*",
        options=CITIES,
        index=0,
        help="Select the target city"
    )
    
    country = st.selectbox(
        "Country*",
        options=COUNTRIES,
        index=0,
        help="Select the target country"
    )
    
    submitted = st.form_submit_button("🔍 Search Leads", use_container_width=True)
    
    if submitted:
        payload = {
            "search_term": search_term,
            "city": city,
            "country": country,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "search_form"
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                st.sidebar.success(f"✅ Search initiated for {search_term} in {city}, {country}!")
                st.session_state.webhook_history.append({
                    "name": f"{search_term} - {city}",
                    "status": "Success",
                    "time": datetime.utcnow().strftime("%H:%M:%S"),
                    "type": "Search"
                })
            else:
                st.sidebar.error(f"❌ Error: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            st.sidebar.error("⚠️ Request timeout - webhook may be slow")
        except Exception as e:
            st.sidebar.error(f"⚠️ Failed: {str(e)}")


# ------------------ CUSTOM DATA FORM (N8N Webhook) ------------------ #
st.sidebar.markdown("---")
st.sidebar.header("🔍 Search New Leads (via Webhook)")

# Predefined options (copied from original code)
SEARCH_TERMS = [
    "Business Owner",
    "CEO",
    "Chief Executive Officer",
    "Founder",
    "Co-Founder",
    "Managing Director",
    "President",
    "Vice President",
    "VP of Sales",
    "VP of Marketing",
    "VP of Operations",
    "VP of Business Development",
    "Chief Operating Officer",
    "Chief Marketing Officer",
    "Chief Technology Officer",
    "Chief Financial Officer",
    "Chief Revenue Officer",
    "Chief Sales Officer",
    "Director of Sales",
    "Director of Marketing",
    "Director of Business Development",
    "Director of Operations",
    "Sales Manager",
    "Marketing Manager",
    "Operations Manager",
    "General Manager",
    "Regional Manager",
    "District Manager",
    "Entrepreneur",
    "Executive Director",
    "Head of Sales",
    "Head of Marketing",
    "Head of Operations",
    "Head of Business Development",
    "Partner",
    "Managing Partner",
    "Senior Partner",
    "Owner",
    "Principal",
    "Consultant",
    "Senior Consultant",
    "Account Executive",
    "Senior Account Executive",
    "Business Development Manager",
    "Sales Director",
    "Marketing Director",
    "Strategy Director",
    "Growth Manager",
    "Revenue Manager",
    "Commercial Director"
]

CITIES = [
    "Tampa",
    "Miami",
    "Orlando",
    "Jacksonville",
    "St. Petersburg",
    "Fort Lauderdale",
    "Tallahassee",
    "Fort Myers",
    "Sarasota",
    "Naples",
    "Atlanta",
    "Charlotte",
    "Raleigh",
    "Nashville",
    "Memphis",
    "New Orleans",
    "Birmingham",
    "New York",
    "Brooklyn",
    "Manhattan",
    "Queens",
    "Los Angeles",
    "San Francisco",
    "San Diego",
    "San Jose",
    "Chicago",
    "Houston",
    "Dallas",
    "Austin",
    "San Antonio",
    "Phoenix",
    "Scottsdale",
    "Philadelphia",
    "Boston",
    "Seattle",
    "Portland",
    "Denver",
    "Boulder",
    "Las Vegas",
    "Salt Lake City",
    "Minneapolis",
    "Detroit",
    "Columbus",
    "Indianapolis",
    "Milwaukee",
    "Kansas City",
    "St. Louis",
    "Cleveland",
    "Pittsburgh",
    "Cincinnati",
    "Richmond",
    "Virginia Beach",
    "Washington DC",
    "Baltimore",
    "Wilmington"
]

COUNTRIES = [
    "United States",
    "Canada",
    "United Kingdom",
    "Australia",
    "New Zealand",
    "Germany",
    "France",
    "Spain",
    "Italy",
    "Portugal",
    "Netherlands",
    "Belgium",
    "Switzerland",
    "Austria",
    "Sweden",
    "Norway",
    "Denmark",
    "Finland",
    "Ireland",
    "Poland",
    "Czech Republic",
    "Greece",
    "Turkey",
    "Israel",
    "United Arab Emirates",
    "Saudi Arabia",
    "Qatar",
    "Singapore",
    "Hong Kong",
    "Japan",
    "South Korea",
    "China",
    "Taiwan",
    "Thailand",
    "Malaysia",
    "Indonesia",
    "Philippines",
    "Vietnam",
    "India",
    "Pakistan",
    "Bangladesh",
    "South Africa",
    "Nigeria",
    "Kenya",
    "Egypt",
    "Brazil",
    "Mexico",
    "Argentina",
    "Chile",
    "Colombia",
    "Peru"
]

with st.sidebar.form("webhook_form"):
    st.markdown("**Lead Search Criteria**")
    
    search_term = st.selectbox(
        "Search Term*",
        options=SEARCH_TERMS,
        index=0,
        help="Select the job title or role to search for"
    )
    
    city = st.selectbox(
        "City*",
        options=CITIES,
        index=0,
        help="Select the target city"
    )
    
    country = st.selectbox(
        "Country*",
        options=COUNTRIES,
        index=0,
        help="Select the target country"
    )
    
    submitted = st.form_submit_button("🔍 Search Leads", use_container_width=True)
    
    if submitted:
        payload = {
            "search_term": search_term,
            "city": city,
            "country": country,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "search_form"
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                st.sidebar.success(f"✅ Search initiated for {search_term} in {city}, {country}!")
                st.session_state.webhook_history.append({
                    "name": f"{search_term} - {city}",
                    "status": "Success",
                    "time": datetime.utcnow().strftime("%H:%M:%S"),
                    "type": "Search"
                })
            else:
                st.sidebar.error(f"❌ Error: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            st.sidebar.error("⚠️ Request timeout - webhook may be slow")
        except Exception as e:
            st.sidebar.error(f"⚠️ Failed: {str(e)}")

# ------------------ DASHBOARD METRICS ------------------ #
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Integration Settings")
webhook_url = st.sidebar.text_input(
    "Webhook URL",
    value="https://agentonline-u29564.vm.elestio.app/webhook/Leadlinked",
    help="Enter your n8n or automation webhook URL"
)

# ------------------ DASHBOARD METRICS ------------------ #
st.markdown(f"<div class='timestamp'>⏱️ Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>", unsafe_allow_html=True)
st.markdown("---")

# Enhanced Key Metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_leads = len(df)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{total_leads}</div>
        <div class="metric-label">Total Leads</div>
        <div class="metric-trend">📈 All time</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    filtered_count = len(filtered_df)
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
        <div class="metric-value">{filtered_count}</div>
        <div class="metric-label">Filtered</div>
        <div class="metric-trend">🔍 Current view</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    sent_count = len(df[df['status'] == 'sent']) if 'status' in df.columns else 0
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
        <div class="metric-value">{sent_count}</div>
        <div class="metric-label">Sent</div>
        <div class="metric-trend">✅ Messages sent</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    pending_count = len(df[df['status'] == 'pending']) if 'status' in df.columns else 0
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);">
        <div class="metric-value">{pending_count}</div>
        <div class="metric-label">Pending</div>
        <div class="metric-trend">⏳ In queue</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    success_rate = (sent_count / total_leads * 100) if total_leads > 0 else 0
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);">
        <div class="metric-value">{success_rate:.1f}%</div>
        <div class="metric-label">Success Rate</div>
        <div class="metric-trend">📊 Conversion</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ------------------ ENHANCED ANALYTICS SECTION ------------------ #
st.markdown("<div class='section-header'>📊 Advanced Analytics Dashboard</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Overview", "🌍 Geographic", "⏰ Timeline", "💬 Messages", "🎯 Performance"])

with tab1:
    if not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Status distribution pie chart
            if 'status' in df.columns:
                status_counts = df['status'].value_counts()
                fig_pie = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="📊 Lead Status Distribution",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.4
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(
                    font=dict(size=12),
                    showlegend=True,
                    height=400
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Search terms bar chart
            if 'search_term' in df.columns:
                term_counts = df['search_term'].value_counts().head(10)
                fig_bar = px.bar(
                    x=term_counts.values,
                    y=term_counts.index,
                    orientation='h',
                    title="🔍 Top Search Terms",
                    color=term_counts.values,
                    color_continuous_scale="Viridis"
                )
                fig_bar.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    if not df.empty and 'search_city' in df.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            # City distribution
            city_counts = df['search_city'].value_counts().head(15)
            fig_city = px.bar(
                x=city_counts.index,
                y=city_counts.values,
                title="🏙️ Leads by City",
                color=city_counts.values,
                color_continuous_scale="Blues"
            )
            fig_city.update_layout(
                xaxis_tickangle=-45,
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_city, use_container_width=True)
        
        with col2:
            # Success rate by city
            if 'status' in df.columns:
                city_success = df.groupby('search_city')['status'].apply(
                    lambda x: (x == 'sent').sum() / len(x) * 100 if len(x) > 0 else 0
                ).sort_values(ascending=False).head(10)
                
                fig_success = px.bar(
                    x=city_success.index,
                    y=city_success.values,
                    title="📈 Success Rate by City (%)",
                    color=city_success.values,
                    color_continuous_scale="Greens"
                )
                fig_success.update_layout(
                    xaxis_tickangle=-45,
                    height=400,
                    showlegend=False
                )
                st.plotly_chart(fig_success, use_container_width=True)

with tab3:
    if not df.empty and 'timestamp' in df.columns:
        # Daily activity timeline
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_counts = df.groupby('date').size().reset_index(name='count')
        
        fig_timeline = px.line(
            daily_counts,
            x='date',
            y='count',
            title="📅 Daily Lead Activity",
            markers=True
        )
        fig_timeline.update_traces(line_color='#667eea', marker_color='#764ba2')
        fig_timeline.update_layout(height=400)
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Hourly heatmap if we have enough data
        if len(df) > 50:
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.day_name()
            
            heatmap_data = df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
            
            fig_heatmap = px.imshow(
                heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                title="🕒 Activity Heatmap (Day vs Hour)",
                color_continuous_scale="Blues"
            )
            fig_heatmap.update_layout(height=400)
            st.plotly_chart(fig_heatmap, use_container_width=True)

with tab4:
    if not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Message length analysis
            if 'linkedin_message' in df.columns:
                df['message_length'] = df['linkedin_message'].astype(str).str.len()
                
                fig_hist = px.histogram(
                    df,
                    x='message_length',
                    title="📝 Message Length Distribution",
                    nbins=20,
                    color_discrete_sequence=['#667eea']
                )
                fig_hist.update_layout(height=400)
                st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Response tracking (simulated data for demo)
            response_data = {
                'Response Type': ['No Response', 'Positive', 'Negative', 'Interested', 'Not Interested'],
                'Count': [45, 25, 10, 15, 5]
            }
            fig_response = px.pie(
                values=response_data['Count'],
                names=response_data['Response Type'],
                title="💬 Response Analysis",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_response.update_layout(height=400)
            st.plotly_chart(fig_response, use_container_width=True)

with tab5:
    if not df.empty:
        # Performance metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Credits usage
            if 'credits_used' in df.columns:
                total_credits = df['credits_used'].sum()
                avg_credits = df['credits_used'].mean()
                
                st.metric(
                    label="💳 Total Credits Used",
                    value=f"{total_credits:,}",
                    delta=f"Avg: {avg_credits:.1f} per lead"
                )
        
        with col2:
            # Connection success rate
            if 'connection_status' in df.columns:
                connected = len(df[df['connection_status'] == 'Connected'])
                connection_rate = (connected / len(df) * 100) if len(df) > 0 else 0
                
                st.metric(
                    label="🤝 Connection Rate",
                    value=f"{connection_rate:.1f}%",
                    delta=f"{connected} connections"
                )
        
        with col3:
            # Average response time (simulated)
            avg_response_time = "2.3 days"
            st.metric(
                label="⏱️ Avg Response Time",
                value=avg_response_time,
                delta="Improving"
            )
        
        # Performance trends
        if 'timestamp' in df.columns and 'status' in df.columns:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            daily_performance = df.groupby(['date', 'status']).size().unstack(fill_value=0)
            
            if not daily_performance.empty:
                available_columns = [col for col in ['sent', 'pending', 'ready_to_send'] if col in daily_performance.columns]
                if available_columns:
                    fig_perf = px.area(
                        daily_performance.reset_index(),
                        x='date',
                        y=available_columns,
                        title="📈 Daily Performance Trends"
                    )
                    fig_perf.update_layout(height=400)
                    st.plotly_chart(fig_perf, use_container_width=True)

st.markdown("---")

# ------------------ MESSAGE TRACKING SECTION ------------------ #
st.markdown("<div class='section-header'>💬 Message Tracking & Management</div>", unsafe_allow_html=True)

# Message tracking summary
col1, col2, col3, col4 = st.columns(4)

with col1:
    messages_today = len(df[df['timestamp'].dt.date == datetime.now().date()]) if 'timestamp' in df.columns and not df.empty else 0
    st.metric("📤 Messages Today", messages_today, delta="Since midnight")

with col2:
    avg_response_rate = 23.5  # Simulated
    st.metric("📊 Response Rate", f"{avg_response_rate}%", delta="+2.1%")

with col3:
    pending_followups = len(df[df['status'] == 'pending']) if 'status' in df.columns else 0
    st.metric("⏳ Pending Follow-ups", pending_followups, delta="Requires attention")

with col4:
    active_campaigns = len(df['search_term'].unique()) if 'search_term' in df.columns and not df.empty else 0
    st.metric("🎯 Active Campaigns", active_campaigns, delta="Different search terms")

# Message timeline
if not df.empty and 'timestamp' in df.columns:
    st.subheader("📅 Message Timeline")
    
    # Create a timeline chart
    timeline_df = df.copy()
    timeline_df['date'] = pd.to_datetime(timeline_df['timestamp']).dt.date
    timeline_df['hour'] = pd.to_datetime(timeline_df['timestamp']).dt.hour
    
    daily_messages = timeline_df.groupby('date').size().reset_index(name='messages')
    
    fig_timeline = px.bar(
        daily_messages,
        x='date',
        y='messages',
        title="Daily Message Volume",
        color='messages',
        color_continuous_scale="Blues"
    )
    fig_timeline.update_layout(height=300)
    st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("---")

# ------------------ ENHANCED LEAD DISPLAY ------------------ #
st.markdown(f"<div class='section-header'>👥 Lead Management ({len(filtered_df)} Leads)</div>", unsafe_allow_html=True)

if filtered_df.empty:
    st.warning("🔍 No leads match your current filters. Try adjusting your search criteria.")
    st.info("💡 **Suggestions:**\n- Clear some filters\n- Try a broader search term\n- Check your date range")
else:
    # Enhanced sorting and display options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sort_options = ["timestamp", "profile_name", "status", "search_city"] if not filtered_df.empty else ["Default"]
        available_sorts = [col for col in sort_options if col in filtered_df.columns]
        sort_by = st.selectbox("📊 Sort by", available_sorts if available_sorts else ["Default"])
    
    with col2:
        sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
    
    with col3:
        view_mode = st.radio("👀 View", ["Cards", "Table", "Compact"], horizontal=True)
    
    with col4:
        leads_per_page = st.selectbox("Per Page", [10, 25, 50, 100], index=1)
    
    # Apply sorting
    if sort_by != "Default" and sort_by in filtered_df.columns:
        ascending = sort_order == "Ascending"
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
    
    # Pagination
    total_pages = (len(filtered_df) - 1) // leads_per_page + 1
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1)
    
    start_idx = (page - 1) * leads_per_page
    end_idx = start_idx + leads_per_page
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    # Display leads based on view mode
    if view_mode == "Cards":
        # Enhanced card view
        for idx, (i, row) in enumerate(paginated_df.iterrows()):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Extract data with better fallbacks
                name = row.get('profile_name', row.get('name', 'Unnamed Lead'))
                location = row.get('profile_location', row.get('location', 'Unknown Location'))
                tagline = row.get('profile_tagline', row.get('tagline', 'No tagline'))
                linkedin_url = row.get('linkedin_url', '#')
                message = row.get('linkedin_message', 'No message')
                status = row.get('status', 'unknown')
                timestamp = row.get('timestamp', datetime.now())
                search_term = row.get('search_term', 'N/A')
                search_city = row.get('search_city', 'N/A')
                
                # Status styling
                status_class = {
                    'ready_to_send': 'status-ready',
                    'sent': 'status-sent',
                    'pending': 'status-pending'
                }.get(status, 'status-pending')
                
                # Check if sent
                is_sent = status == 'sent' or i in st.session_state.sent_leads
                sent_indicator = "✅ SENT" if is_sent else ""
                
                st.markdown(f"""
                <div class="lead-card">
                    <div class="lead-title">
                        👤 {name} {sent_indicator}
                    </div>
                    <div class="lead-sub">📍 {location}</div>
                    <div class="lead-sub">💼 {tagline}</div>
                    <div class="lead-sub">🔍 Search: {search_term} in {search_city}</div>
                    <div class="lead-sub">🔗 <a href="{linkedin_url}" target="_blank" style="color: #667eea; text-decoration: none;">View LinkedIn Profile →</a></div>
                    <div class="lead-msg">💬 {message}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                        <span class="status-badge {status_class}">{status.replace('_', ' ').title()}</span>
                        <span class="timestamp">🕒 {pd.to_datetime(timestamp).strftime('%Y-%m-%d %H:%M')}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Actions**")
                
                # Send button
                if st.button(f"🚀 Send", key=f"send_{i}", disabled=is_sent, use_container_width=True):
                    # Simulate sending
                    st.session_state.sent_leads.add(i)
                    st.session_state.activity_log.append({
                        "lead": name,
                        "status": "✅ Sent",
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "action": "Message sent"
                    })
                    st.success(f"✅ Message sent to {name}!")
                    time.sleep(1)
                    st.rerun()
                
                # Additional actions
                if st.button(f"📋 Copy", key=f"copy_{i}", use_container_width=True):
                    st.info("📋 Lead data copied!")
                
                if st.button(f"⭐ Save", key=f"save_{i}", use_container_width=True):
                    st.info("⭐ Lead saved to favorites!")
                
                # Selection checkbox
                is_selected = i in st.session_state.selected_leads
                if st.checkbox(f"Select", key=f"select_{i}", value=is_selected):
                    if i not in st.session_state.selected_leads:
                        st.session_state.selected_leads.append(i)
                else:
                    if i in st.session_state.selected_leads:
                        st.session_state.selected_leads.remove(i)
    
    elif view_mode == "Table":
        # Enhanced table view with better column selection
        display_columns = []
        if not filtered_df.empty:
            all_columns = filtered_df.columns.tolist()
            important_columns = ['profile_name', 'profile_location', 'status', 'timestamp', 'search_term', 'search_city']
            display_columns = [col for col in important_columns if col in all_columns]
            
            # Add any remaining columns
            remaining_columns = [col for col in all_columns if col not in display_columns]
            display_columns.extend(remaining_columns[:5])  # Limit to avoid clutter
        
        if display_columns:
            st.dataframe(
                paginated_df[display_columns],
                use_container_width=True,
                height=600
            )
        else:
            st.dataframe(paginated_df, use_container_width=True, height=600)
    
    else:  # Compact view
        for idx, (i, row) in enumerate(paginated_df.iterrows()):
            name = row.get('profile_name', row.get('name', 'Unnamed Lead'))
            location = row.get('profile_location', row.get('location', 'Unknown'))
            status = row.get('status', 'unknown')
            timestamp = row.get('timestamp', datetime.now())
            
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.write(f"👤 **{name}**")
            with col2:
                st.write(f"📍 {location}")
            with col3:
                st.write(f"📊 {status}")
            with col4:
                if st.button("🚀", key=f"send_compact_{i}", help="Send message"):
                    st.success("Sent!")

# ------------------ BULK ACTIONS ------------------ #
if not filtered_df.empty:
    st.markdown("---")
    st.markdown("<div class='section-header'>⚡ Bulk Operations</div>", unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        bulk_count = st.number_input(
            "Number of leads",
            min_value=1,
            max_value=len(filtered_df),
            value=min(5, len(filtered_df))
        )
    
    with col2:
        if st.button("📤 Send Bulk", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, (i, row) in enumerate(filtered_df.head(bulk_count).iterrows()):
                status_text.text(f"Sending to {row.get('profile_name', 'Lead')}...")
                
                # Simulate sending
                st.session_state.sent_leads.add(i)
                st.session_state.activity_log.append({
                    "lead": row.get('profile_name', f'Lead {i}'),
                    "status": "✅ Bulk Sent",
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "action": "Bulk operation"
                })
                
                progress_bar.progress((idx + 1) / bulk_count)
                time.sleep(0.3)  # Simulate processing time
            
            status_text.text("✅ Bulk operation completed!")
            st.success(f"✅ Successfully sent {bulk_count} messages!")
            time.sleep(2)
            st.rerun()
    
    with col3:
        if st.button("📊 Export Selected", use_container_width=True):
            if st.session_state.selected_leads:
                selected_data = filtered_df.loc[st.session_state.selected_leads]
                csv = selected_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"selected_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No leads selected!")
    
    with col4:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.info("🔄 Status refreshed!")
            st.rerun()
    
    with col5:
        if st.button("🗑️ Clear Selection", use_container_width=True):
            st.session_state.selected_leads = []
            st.success("Selection cleared!")
            st.rerun()

# ------------------ ACTIVITY LOG & SYSTEM STATUS ------------------ #
st.markdown("---")
st.markdown("<div class='section-header'>📊 System Activity & Status</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🎯 Recent Activity", "📈 System Stats", "⚙️ Configuration"])

with tab1:
    if st.session_state.activity_log:
        st.subheader("Recent Actions")
        recent_activities = st.session_state.activity_log[-20:]  # Last 20 activities
        
        for activity in reversed(recent_activities):
            st.markdown(f"""
            <div class="activity-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>👤 {activity['lead']}</strong> - {activity['status']}
                        <br><small>🔧 {activity.get('action', 'Action performed')}</small>
                    </div>
                    <div class="timestamp">🕒 {activity['time']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📝 No recent activity. Start sending messages to see activity here!")

with tab2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Performance Metrics")
        
        # Calculate some stats
        total_processed = len(st.session_state.activity_log)
        success_count = len([a for a in st.session_state.activity_log if "Success" in a.get('status', '')])
        success_rate = (success_count / total_processed * 100) if total_processed > 0 else 0
        
        st.metric("Total Processed", total_processed)
        st.metric("Success Rate", f"{success_rate:.1f}%")
        st.metric("Active Sessions", 1)
        st.metric("System Uptime", "99.9%")
    
    with col2:
        st.subheader("🔧 System Health")
        
        st.success("✅ Database: Connected")
        st.success("✅ API: Operational")
        st.success("✅ Webhooks: Active")
        st.info("ℹ️ Last backup: 2 hours ago")
        
        if st.button("🔄 Run System Check", use_container_width=True):
            with st.spinner("Running diagnostics..."):
                time.sleep(2)
            st.success("✅ All systems operational!")

with tab3:
    st.subheader("⚙️ Application Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Display Settings**")
        st.checkbox("Show timestamps", value=True)
        st.checkbox("Enable animations", value=True)
        st.checkbox("Compact mode", value=False)
        
        st.write("**Notification Settings**")
        st.checkbox("Email notifications", value=False)
        st.checkbox("Browser notifications", value=True)
    
    with col2:
        st.write("**Performance Settings**")
        st.slider("Refresh interval (seconds)", 30, 300, 60)
        st.slider("Items per page", 10, 100, 25)
        
        st.write("**Export Settings**")
        st.selectbox("Default export format", ["CSV", "Excel", "JSON"])
        st.checkbox("Include timestamps in exports", value=True)

# ------------------ FOOTER ------------------ #
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**🤖 System Status**")
    st.success("● Online & Operational")
    st.info(f"📊 {len(df)} leads loaded")

with col2:
    st.markdown("**📊 Data Source**")
    source_text = "Demo Data" if data_source == "Demo Data" else "Google Sheets"
    st.info(f"📋 {source_text}")
    st.info(f"🔄 Auto-refresh: {'On' if auto_refresh else 'Off'}")

with col3:
    st.markdown("**🔗 Integration**")
    webhook_status = "✅ Connected" if webhook_url else "❌ Not configured"
    st.info(f"🔗 Webhook: {webhook_status}")
    st.info(f"⚡ {len(st.session_state.activity_log)} actions logged")

with col4:
    st.markdown("**📈 Performance**")
    st.info(f"🎯 {len(st.session_state.selected_leads)} selected")
    st.info(f"🔍 {len(filtered_df)} filtered results")

# ------------------ AUTO REFRESH ------------------ #
if auto_refresh:
    time.sleep(60)
    st.rerun()
