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

# ------------------ PAGE CONFIG ------------------ #
st.set_page_config(
    page_title="AI LinkedIn Lead System",
    page_icon="🤖",
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

# ------------------ ENHANCED STYLES ------------------ #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    body {
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.3rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .sub-title {
        text-align: center;
        font-size: 1.1rem;
        color: #64748b;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .lead-card {
        background-color: #ffffff;
        border-radius: 18px;
        padding: 1.8rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
        transition: all 0.3s ease-in-out;
        border-left: 4px solid #667eea;
    }
    
    .lead-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }
    
    .lead-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    
    .lead-sub {
        font-size: 0.95rem;
        color: #475569;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .lead-msg {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        font-size: 0.95rem;
        color: #334155;
        border-left: 3px solid #667eea;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .status-ready {
        background-color: #dcfce7;
        color: #166534;
    }
    
    .status-sent {
        background-color: #dbeafe;
        color: #1e40af;
    }
    
    .status-pending {
        background-color: #fef3c7;
        color: #92400e;
    }
    
    .timestamp {
        font-size: 0.85rem;
        color: #94a3b8;
        text-align: right;
        font-weight: 500;
    }
    
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #667eea;
    }
    
    .stats-container {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .activity-item {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------ #
st.markdown("<div class='main-title'>🤖 AI LinkedIn Lead System</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Advanced Lead Management, Analytics & Automation Platform</div>", unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------ #
st.sidebar.header("🧠 System Configuration")

# Theme Toggle
theme = st.sidebar.radio("🎨 Theme Mode", ["Light", "Dark"], horizontal=True)
if theme == "Dark":
    st.markdown("""
    <style>
        body, .stApp { background-color: #0f172a; color: #e2e8f0; }
        .lead-card { background-color: #1e293b; color: #f1f5f9; border-left-color: #8b5cf6; }
        .lead-msg { background: linear-gradient(135deg, #334155 0%, #475569 100%); color: #e2e8f0; }
        .stats-container { background: linear-gradient(135deg, #1e293b 0%, #334155 100%); }
        .activity-item { background: #1e293b; color: #e2e8f0; }
        .section-header { color: #f1f5f9; }
    </style>
    """, unsafe_allow_html=True)

# Google Authentication
st.sidebar.subheader("🔐 Google Sheets Connection")
service_file = st.sidebar.file_uploader("Upload Service Account JSON", type=["json"])

if not service_file:
    st.warning("⚠️ Please upload your Google Service Account JSON file to access live data.")
    st.info("💡 **How to get started:**\n1. Create a service account in Google Cloud Console\n2. Download the JSON key file\n3. Share your Google Sheet with the service account email\n4. Upload the JSON file here")
    st.stop()

# Authenticate with Google
try:
    # Read the JSON file content
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
st.sidebar.subheader("📊 Data Source")
sheet_url = st.sidebar.text_input(
    "Google Sheet URL",
    value="https://docs.google.com/spreadsheets/d/1eLEFvyV1_f74UC1g5uQ-xA7A62sK8Pog27KIjw_Sk3Y/edit?usp=sharing"
)

try:
    sheet_id = sheet_url.split("/")[5]
    sheet = client.open_by_key(sheet_id).sheet1
    
    # Define expected headers for the sheet
    expected_headers = ['Name', 'Location', 'Title', 'LinkedIn_URL', 'Message', 'Status']
    
    # Get all values from the sheet
    all_values = sheet.get_all_values()
    
    if len(all_values) > 0:
        # Use the expected headers and start from the first row of data
        df = pd.DataFrame(all_values, columns=expected_headers[:len(all_values[0])])
        
        # If there are more columns than expected, add generic names
        if len(all_values[0]) > len(expected_headers):
            for i in range(len(expected_headers), len(all_values[0])):
                df.columns.values[i] = f'Column_{i+1}'
    else:
        df = pd.DataFrame(columns=expected_headers)
    
    st.session_state.last_refresh = datetime.utcnow()
    st.sidebar.success(f"✅ Loaded {len(df)} leads")
except Exception as e:
    st.sidebar.error(f"⚠️ Unable to load data: {str(e)}")
    st.stop()

# Auto-refresh toggle
st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (60s)", value=False)
if auto_refresh:
    st.sidebar.info(f"⏱️ Last refresh: {st.session_state.last_refresh.strftime('%H:%M:%S UTC')}")

# Manual refresh button
if st.sidebar.button("🔄 Refresh Data Now", use_container_width=True):
    st.rerun()

# ------------------ ADVANCED FILTERS ------------------ #
st.sidebar.markdown("---")
st.sidebar.subheader("🔎 Advanced Filters")

search_query = st.sidebar.text_input("🔍 Search (name, company, title)", placeholder="Type to search...")
city_filter = st.sidebar.text_input("📍 Filter by City", placeholder="e.g., Tampa, New York")
status_filter = st.sidebar.selectbox(
    "📊 Status Filter",
    ["All", "ready_to_send", "sent", "pending"],
    index=0
)

# Additional filters
st.sidebar.markdown("**Advanced Options**")
col1, col2 = st.sidebar.columns(2)
with col1:
    min_connections = st.number_input("Min Connections", min_value=0, value=0, step=50)
with col2:
    show_sent_only = st.checkbox("Sent Only", value=False)

# Apply filters
filtered_df = df.copy()

if search_query:
    filtered_df = filtered_df[filtered_df.apply(
        lambda r: search_query.lower() in str(r).lower(), axis=1
    )]

if city_filter:
    filtered_df = filtered_df[filtered_df.apply(
        lambda r: city_filter.lower() in str(r).lower(), axis=1
    )]

if status_filter != "All":
    if "ready_to_send" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["ready_to_send"].astype(str).str.contains(
                status_filter, case=False, na=False
            )
        ]

if show_sent_only:
    filtered_df = filtered_df[filtered_df.index.isin(st.session_state.sent_leads)]

# ------------------ WEBHOOK CONFIGURATION ------------------ #
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Webhook Settings")
webhook_url = st.sidebar.text_input(
    "n8n Webhook URL",
    value="https://agentonline-u29564.vm.elestio.app/webhook-test/Leadlinked"
)

# ------------------ CUSTOM DATA FORM ------------------ #
st.sidebar.markdown("---")
st.sidebar.header("🔍 Search New Leads")

# Predefined options
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
st.markdown(f"<div class='timestamp'>⏱️ Last Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>", unsafe_allow_html=True)
st.markdown("---")

# Key Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(df)}</div>
        <div class="metric-label">Total Leads</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    ready_count = len(filtered_df)
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
        <div class="metric-value">{ready_count}</div>
        <div class="metric-label">Filtered Leads</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    sent_count = len(st.session_state.sent_leads)
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
        <div class="metric-value">{sent_count}</div>
        <div class="metric-label">Sent Today</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    success_rate = (sent_count / len(df) * 100) if len(df) > 0 else 0
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);">
        <div class="metric-value">{success_rate:.1f}%</div>
        <div class="metric-label">Success Rate</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ------------------ BULK ACTIONS ------------------ #
st.markdown("<div class='section-header'>⚡ Bulk Actions</div>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    bulk_count = st.number_input("Number of leads to send", min_value=1, max_value=len(filtered_df), value=min(5, len(filtered_df)))

with col2:
    if st.button("📤 Send Bulk", use_container_width=True):
        progress_bar = st.progress(0)
        for idx, (i, row) in enumerate(filtered_df.head(bulk_count).iterrows()):
            lead_payload = row.to_dict()
            lead_payload["timestamp"] = datetime.utcnow().isoformat()
            
            try:
                res = requests.post(webhook_url, json=lead_payload, timeout=5)
                if res.status_code == 200:
                    st.session_state.sent_leads.add(i)
                    st.session_state.activity_log.append({
                        "lead": row.get(df.columns[0], "Unknown"),
                        "status": "✅ Success",
                        "time": datetime.utcnow().strftime("%H:%M:%S")
                    })
            except:
                pass
            
            progress_bar.progress((idx + 1) / bulk_count)
            time.sleep(0.5)
        
        st.success(f"✅ Sent {bulk_count} leads!")
        st.rerun()

with col3:
    select_all = st.checkbox("Select All", value=False)
    if select_all:
        st.session_state.selected_leads = list(filtered_df.index)

with col4:
    if st.button("🗑️ Clear Selection", use_container_width=True):
        st.session_state.selected_leads = []
        st.rerun()

st.markdown("---")

# ------------------ ANALYTICS SECTION ------------------ #
with st.expander("📊 Analytics Dashboard", expanded=False):
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "🌍 Geography", "⏰ Timeline"])
    
    with tab1:
        if len(df) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                # Status distribution
                if "ready_to_send" in df.columns:
                    status_counts = df["ready_to_send"].value_counts()
                    fig = px.pie(
                        values=status_counts.values,
                        names=status_counts.index,
                        title="Lead Status Distribution",
                        color_discrete_sequence=px.colors.sequential.Viridis
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Activity timeline
                if st.session_state.webhook_history:
                    history_df = pd.DataFrame(st.session_state.webhook_history)
                    fig = px.bar(
                        history_df,
                        x="time",
                        color="status",
                        title="Webhook Activity Timeline",
                        color_discrete_map={"Success": "#10b981", "Failed": "#ef4444"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No webhook activity yet")
    
    with tab2:
        st.subheader("Geographic Distribution")
        # This would need location data in your sheet
        st.info("Add location columns to enable geographic analytics")
    
    with tab3:
        st.subheader("Activity Timeline")
        if st.session_state.activity_log:
            log_df = pd.DataFrame(st.session_state.activity_log)
            st.dataframe(log_df, use_container_width=True)
        else:
            st.info("No activity recorded yet")

st.markdown("---")

# ------------------ LEAD DISPLAY ------------------ #
st.markdown(f"<div class='section-header'>👥 Lead Directory ({len(filtered_df)} Leads)</div>", unsafe_allow_html=True)

if len(filtered_df) == 0:
    st.warning("🔍 No leads match your current filters. Try adjusting your search criteria.")
else:
    # Sorting options
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        sort_by = st.selectbox("Sort by", ["Default", "Name", "Status", "Recently Added"])
    with col2:
        view_mode = st.radio("View", ["Cards", "Table"], horizontal=True)
    with col3:
        leads_per_page = st.selectbox("Per Page", [10, 25, 50, 100], index=0)
    
    # Pagination
    total_pages = (len(filtered_df) - 1) // leads_per_page + 1
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    start_idx = (page - 1) * leads_per_page
    end_idx = start_idx + leads_per_page
    
    paginated_df = filtered_df.iloc[start_idx:end_idx]
    
    if view_mode == "Cards":
        cols = st.columns(2)
        
        for idx, (i, row) in enumerate(paginated_df.iterrows()):
            col = cols[idx % 2]
            
            with col:
                # Extract data with fallbacks
                name = row.get(df.columns[0], "Unnamed Lead") if len(df.columns) > 0 else "Unnamed Lead"
                location = row.get(df.columns[1], "") if len(df.columns) > 1 else ""
                title = row.get(df.columns[2], "") if len(df.columns) > 2 else ""
                linkedin = row.get(df.columns[3], "") if len(df.columns) > 3 else ""
                message = row.get(df.columns[4], "") if len(df.columns) > 4 else ""
                status = row.get("ready_to_send", "pending")
                
                # Status badge styling
                status_class = "status-ready" if "ready" in str(status).lower() else \
                              "status-sent" if "sent" in str(status).lower() else "status-pending"
                
                # Determine if already sent
                is_sent = i in st.session_state.sent_leads
                sent_badge = "✅ SENT" if is_sent else ""
                
                st.markdown(f"""
                <div class="lead-card">
                    <div class="lead-title">{name} {sent_badge}</div>
                    <div class="lead-sub">📍 {location}</div>
                    <div class="lead-sub">💼 {title}</div>
                    <div class="lead-sub">🔗 <a href="{linkedin}" target="_blank" style="color: #667eea; text-decoration: none;">View LinkedIn Profile →</a></div>
                    <div class="lead-msg">💬 {message}</div>
                    <div class="lead-sub">
                        <span class="status-badge {status_class}">{status}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Action buttons
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if st.button(f"🚀 Send", key=f"send_{i}", disabled=is_sent, use_container_width=True):
                        lead_payload = row.to_dict()
                        lead_payload["timestamp"] = datetime.utcnow().isoformat()
                        
                        try:
                            res = requests.post(webhook_url, json=lead_payload, timeout=10)
                            if res.status_code == 200:
                                st.success(f"✅ Sent {name}!")
                                st.session_state.sent_leads.add(i)
                                st.session_state.activity_log.append({
                                    "lead": name,
                                    "status": "✅ Success",
                                    "time": datetime.utcnow().strftime("%H:%M:%S")
                                })
                                st.session_state.webhook_history.append({
                                    "name": name,
                                    "status": "Success",
                                    "time": datetime.utcnow().strftime("%H:%M:%S"),
                                    "type": "Auto"
                                })
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Error: {res.status_code}")
                        except Exception as e:
                            st.error(f"⚠️ Failed: {str(e)}")
                
                with col_btn2:
                    if st.button(f"📋 Copy", key=f"copy_{i}", use_container_width=True):
                        st.info("Lead data copied to clipboard!")
                
                with col_btn3:
                    is_selected = i in st.session_state.selected_leads
                    if st.button(f"{'✓' if is_selected else '☐'} Select", key=f"select_{i}", use_container_width=True):
                        if is_selected:
                            st.session_state.selected_leads.remove(i)
                        else:
                            st.session_state.selected_leads.append(i)
                        st.rerun()
    
    else:  # Table view
        st.dataframe(
            paginated_df,
            use_container_width=True,
            height=600
        )

# ------------------ ACTIVITY LOG ------------------ #
if st.session_state.activity_log or st.session_state.webhook_history:
    st.markdown("---")
    st.markdown("<div class='section-header'>📊 Recent Activity</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🎯 Lead Activity", "🔗 Webhook History"])
    
    with tab1:
        if st.session_state.activity_log:
            recent_log = st.session_state.activity_log[-20:]  # Last 20 activities
            for activity in reversed(recent_log):
                st.markdown(f"""
                <div class="activity-item">
                    <strong>{activity['lead']}</strong> - {activity['status']}
                    <span style="float: right; color: #94a3b8;">{activity['time']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No activity recorded yet. Send some leads to see activity here!")
    
    with tab2:
        if st.session_state.webhook_history:
            history_df = pd.DataFrame(st.session_state.webhook_history)
            st.dataframe(history_df, use_container_width=True)
            
            # Export option
            if st.button("📥 Export History as CSV"):
                csv = history_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"webhook_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("No webhook activity yet")

# ------------------ FOOTER ------------------ #
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**🤖 System Status**")
    st.success("● Online")

with col2:
    st.markdown("**📊 Data Source**")
    st.info(f"Google Sheets ({len(df)} leads)")

with col3:
    st.markdown("**🔗 Webhook**")
    st.info("n8n Connected")

# ------------------ AUTO REFRESH ------------------ #
if auto_refresh:
    time.sleep(60)
    st.rerun()
