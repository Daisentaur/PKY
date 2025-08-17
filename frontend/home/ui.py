import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
from datetime import datetime
import ast


@st.cache_resource
def init_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"Failed to initialize Supabase client: {str(e)}")
        return None

supabase = init_supabase()


def fetch_document_sessions():
    """Fetch document sessions from Supabase with error handling"""
    if not supabase:
        st.error("Supabase client not initialized")
        return None
    
    try:
        response = supabase.table("document_sessions").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return pd.DataFrame()



st.title(" Insurance Analyser")
st.write("Welcome to the Insurance Analyser!")
st.write("")
st.write("")


# Responsive design for small screens -----------------------------
st.markdown("""
    <style>
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .element-container {
            margin-left: 0rem !important;
            margin-right: 0rem !important;
        }
        /* Stack columns vertically on mobile */
        .css-1l269bu, .css-1kyxreq {
            flex-direction: column !important;
        }
    }
    </style>
""", unsafe_allow_html=True)



# Fetch all documents from Supabase
df = fetch_document_sessions()
if df.empty:
    st.warning("No data found in the database")
    st.stop()


# Process metadata safely
def parse_metadata(metadata):
    if isinstance(metadata, str):
        try:
            return ast.literal_eval(metadata)
        except:
            return {}
    elif isinstance(metadata, dict):
        return metadata
    return {}

# Process data for KPIs
total_files = len(df)
successful_extractions = sum(1 for _, row in df.iterrows() if row.get('extracted_data'))

# Calculate file type distribution
file_types = {}
for _, row in df.iterrows():
    metadata = parse_metadata(row.get('document_metadata', {}))
    if metadata and 'file_types' in metadata:
        file_type = metadata['file_types']
        # Handle case where file_types might be a list
        if isinstance(file_type, list):
            for ft in file_type:
                file_types[ft] = file_types.get(ft, 0) + 1
        else:
            file_types[file_type] = file_types.get(file_type, 0) + 1



# Calculate activity data (last 30 days)
activity_data = {}
for _, row in df.iterrows():
    metadata = parse_metadata(row.get('document_metadata', {}))
    if metadata and 'completed_at' in metadata:
        try:
            date = pd.to_datetime(metadata['completed_at']).date()
            activity_data[date] = activity_data.get(date, 0) + 1
        except:
            continue


# Convert to DataFrames
df_activity = pd.DataFrame(list(activity_data.items()), columns=['date', 'count']).set_index('date')
df_file_types = pd.DataFrame(list(file_types.items()), columns=['format', 'count']).set_index('format')

# KPIs Section
colA, colB, colC = st.columns(3)
colA.metric("Total Files Processed", total_files)
colB.metric("Successful Extractions", successful_extractions)
colC.metric("Success Rate", f"{(successful_extractions / total_files * 100):.1f} %" if total_files > 0 else "0 %")


# Activity Chart
st.markdown("### Activity (last 30 days)")
if not df_activity.empty:
    st.line_chart(df_activity, use_container_width=True)
else:
    st.warning("No activity data available")

# File Type Distribution
st.markdown("### File Type Distribution")
if not df_file_types.empty:
    st.bar_chart(df_file_types, use_container_width=True)
else:
    st.warning("No file type data available")

# Client Statistics
if 'session_id' in df.columns:
    unique_sessions = df['session_id'].nunique()
    avg_files_per_session = total_files / unique_sessions if unique_sessions > 0 else 0
    
    st.markdown("### Client Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sessions", unique_sessions)
    col2.metric("Total Documents", total_files)
    col3.metric("Avg Docs per Session", f"{avg_files_per_session:.1f}")

