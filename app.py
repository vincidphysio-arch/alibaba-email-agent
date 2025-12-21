import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

# 1. Page Configuration
st.set_page_config(
    page_title="Alibaba Vendor Intelligence",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: radial-gradient(circle at top right, #1a1a2e, #16213e, #0f3460);
        color: #e94560;
    }
    
    /* Card-like containers for metrics */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.3s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid #e94560;
    }

    /* Titles and Header */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700 !important;
        background: linear-gradient(90deg, #e94560, #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 52, 96, 0.95) !important;
        border-right: 1px solid rgba(233, 69, 96, 0.2);
    }
    
    /* Dataframe/Table styling */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Info/Success messages */
    .stAlert {
        background: rgba(233, 69, 96, 0.1) !important;
        color: #e94560 !important;
        border: 1px solid rgba(233, 69, 96, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load_data(sheet_id):
    try:
        # 1. Try Service Account (existing method)
        if "GOOGLE_CREDENTIALS" in st.secrets:
            creds_dict = dict(st.secrets["GOOGLE_CREDENTIALS"])
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        # 2. Try OAuth2 Refresh Token (new method, consistent with sync script)
        elif all(k in st.secrets for k in ["OAUTH_CLIENT_ID", "OAUTH_CLIENT_SECRET", "OAUTH_REFRESH_TOKEN"]):
            from google.oauth2.credentials import Credentials as OAuthCredentials
            creds = OAuthCredentials(
                token=None,
                refresh_token=st.secrets["OAUTH_REFRESH_TOKEN"],
                token_uri='https://oauth2.googleapis.com/token',
                client_id=st.secrets["OAUTH_CLIENT_ID"],
                client_secret=st.secrets["OAUTH_CLIENT_SECRET"],
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        else:
            st.error("Credential configuration missing. Please set GOOGLE_CREDENTIALS or OAuth secrets.")
            return pd.DataFrame()

        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # Map Sheet Headers to expected app columns
            # Expected Headers from gmail_sync.py: ['Timestamp', 'Email ID', 'Vendor', 'Summary', 'Quality Score', 'Subject']
            column_mapping = {
                'Timestamp': 'date',
                'Vendor': 'vendor',
                'Summary': 'summary',
                'Quality Score': 'quality_score',
                'Subject': 'subject',
                'From': 'sender'
            }
            # Only rename columns that exist
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # Ensure proper types
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            if 'quality_score' in df.columns:
                df['quality_score'] = pd.to_numeric(df['quality_score'], errors='coerce').fillna(0)
            if 'vendor' in df.columns:
                df['vendor'] = df['vendor'].astype(str)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# 2. Main UI
st.title("🤖 Alibaba Vendor Intelligence Dashboard")
st.markdown("### AI-Powered Analysis of Procurement Communications")

try:
    if "SHEET_ID" in st.secrets:
        SHEET_ID = st.secrets["SHEET_ID"]
        df = load_data(SHEET_ID)
    else:
        st.warning("⚠️ SHEET_ID not found in Streamlit Secrets. Please configure your settings.")
        df = pd.DataFrame()
except Exception as e:
    st.error(f"Configuration Error: {e}")
    df = pd.DataFrame()

# Refresh logic in sidebar
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

if not df.empty:
    # 3. Sidebar Filters
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filters")
    
    # Date Range Logic with NaT safety
    if 'date' in df.columns:
        valid_dates = df['date'].dropna()
        if not valid_dates.empty:
            min_date_val = valid_dates.min().date()
            max_date_val = valid_dates.max().date()
        else:
            max_date_val = datetime.now().date()
            min_date_val = max_date_val - timedelta(days=30)
    else:
        st.warning("Column 'date' not found in data.")
        max_date_val = datetime.now().date()
        min_date_val = max_date_val - timedelta(days=30)
    
    date_range = st.sidebar.date_input("Date Range", value=(min_date_val, max_date_val))    
    
    vendors = ['All'] + sorted(df['vendor'].unique().tolist()) if 'vendor' in df.columns else ['All']
    selected_vendor = st.sidebar.selectbox("Vendor", vendors)    
    
    min_score, max_score = st.sidebar.slider("Quality Score", 0, 10, (0, 10))
    
    # 4. Filtering Logic (Fixes Type Mismatch Error)
    if len(date_range) == 2 and 'date' in df.columns:
        start_dt = pd.to_datetime(date_range[0])
        end_dt = pd.to_datetime(date_range[1])
        
        mask = ((df['date'] >= start_dt) & 
                (df['date'] <= end_dt) &
                (df['quality_score'] >= min_score) & 
                (df['quality_score'] <= max_score))
        
        if selected_vendor != 'All':
            mask &= (df['vendor'] == selected_vendor)
        
        filtered_df = df[mask]
        
        # 5. Dashboard Visuals
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Quotes Analyzed", len(filtered_df))
        col2.metric("🏢 Active Vendors", filtered_df['vendor'].nunique())
        col3.metric("⭐ Reliability Index", f"{filtered_df['quality_score'].mean():.1f}" if not filtered_df.empty else "0.0")
        col4.metric("🏆 Premium Partners", len(filtered_df[filtered_df['quality_score'] >= 8]))
        
        c_left, c_right = st.columns(2)
        with c_left:
            if not filtered_df.empty:
                timeline = filtered_df.groupby(filtered_df['date'].dt.date).size().reset_index()
                timeline.columns = ['Date', 'Count']
                fig_timeline = px.line(timeline, x='Date', y='Count', title='📈 Communications Volume Trend')
                fig_timeline.update_traces(line_color='#e94560')
                st.plotly_chart(fig_timeline, use_container_width=True)
        
        with c_right:
            if not filtered_df.empty:
                fig_hist = px.histogram(filtered_df, x='quality_score', nbins=10, title='📊 Vendor Quality Distribution')
                fig_hist.update_traces(marker_color='#e94560')
                st.plotly_chart(fig_hist, use_container_width=True)
        
        st.subheader("🏆 Strategic Vendor Rankings")
        if not filtered_df.empty:
            vendor_stats = filtered_df.groupby('vendor').agg({'quality_score': 'mean', 'date': 'count'}).reset_index()
            vendor_stats.columns = ['Vendor', 'Avg Quality', 'Volume']
            vendor_stats = vendor_stats.sort_values('Avg Quality', ascending=False).head(10)
            st.plotly_chart(px.bar(
                vendor_stats, 
                x='Vendor', 
                y='Avg Quality', 
                color='Avg Quality', 
                color_continuous_scale='Magma',
                title="Top Performing Partners"
            ), use_container_width=True)
        
        st.subheader("📋 Email Details")
        st.dataframe(filtered_df[['date', 'vendor', 'subject', 'quality_score']].sort_values('date', ascending=False), use_container_width=True)
        
        csv = filtered_df.to_csv(index=False)
        st.download_button("📥 Download CSV", csv, f"alibaba_emails_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
    else:
        st.info("Please select a full date range in the sidebar.")
else:
    st.info("⏳ No data found. Ensure your Google Sheet is connected and contains email records!")

st.sidebar.markdown("---")
st.sidebar.caption(f"🕐 Last Updated: {datetime.now().strftime('%H:%M:%S')}")
