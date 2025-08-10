import streamlit as st
import pandas as pd
import numpy as np
from streamlit_js_eval import streamlit_js_eval

# from supabase import create_client, Client
# @st.cache_resource
# def init_supabase():
#     try:
#         return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
#     except Exception as e:
#         st.error(f"Failed to initialize Supabase client: {str(e)}")
#         return None

# supabase = init_supabase()

# def get_analytics():
#     response = supabase.table("analytics").select("*").order("date", desc=False).limit(30).execute()
#     if response.data:
#         return pd.DataFrame(response.data)
#     else:
#         return pd.DataFrame()


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


 # KPIs -------------------------------------------------------------
colA, colB, colC = st.columns(3)
colA.metric("Total Files Processed", "1 024")
colB.metric("Avg Extraction Time", "1.9 s")
colC.metric("Success Rate", "98 %")
st.markdown("###  Activity (last 30 days)")

dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
df_activity = pd.DataFrame({"date": dates, "docs": np.random.randint(15, 60, size=len(dates))}).set_index("date")
st.line_chart(df_activity, use_container_width=True)

st.markdown("###  Download Format Popularity")
formats = ["JSON", "XML", "TXT", "DOCX", "PDF"]
counts  = np.random.randint(50, 200, size=len(formats))
df_formats = pd.DataFrame({"format": formats, "count": counts}).set_index("format")
st.bar_chart(df_formats, use_container_width=True)

st.markdown("### Client Activity")
col1, col2, col3 = st.columns(3)
col1.metric("Total Clients", "147")
col2.metric("New Clients", "12")
col3.metric("Avg Files per Client", "6.8")
st.markdown("---")
