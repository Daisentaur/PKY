import streamlit as st
import Admin_Page, Client_Page
import pandas as pd
import numpy as np
from streamlit_js_eval import streamlit_js_eval

def main():
    st.title(" Home Page")
    st.write("Welcome to the Home Page!")

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
            }
        </style>
    """, unsafe_allow_html=True)

     # KPIs -------------------------------------------------------------
    if st.session_state.get("is_mobile"):
        # stack vertically
        colA.metric("Total Files Processed", "1 024")
        colB.metric("Avg Extraction Time", "1.9 s")
        colC.metric("Success Rate", "98 %")
    else:
        colA, colB, colC = st.columns(3)
        colA.metric("Total Files Processed", "1 024")
        colB.metric("Avg Extraction Time", "1.9 s")
        colC.metric("Success Rate", "98 %")

    st.markdown("###  Activity (last 30 days)")

    # 🔹 Dummy demo data – replace with real query to your DB ----------
    dates = pd.date_range(end=pd.Timestamp.today(), periods=30)
    df_activity = pd.DataFrame({
        "date": dates,
        "docs": np.random.randint(15, 60, size=len(dates))
    }).set_index("date")

    st.line_chart(df_activity,  use_container_width=True)

    st.markdown("###  Download Format Popularity")

    formats = ["JSON", "XML", "TXT", "DOCX", "PDF"]
    counts  = np.random.randint(50, 200, size=len(formats))
    df_formats = pd.DataFrame({"format": formats, "count": counts}) \
        .set_index("format")

    st.bar_chart(df_formats,  use_container_width=True)



    # ------------------ CLIENT METRICS ------------------
    st.markdown("### 👥 Client Activity")


    if st.session_state.get("is_mobile"):
        # stack vertically
        col1.metric("Total Clients", "147")
        col2.metric("New Clients", "12")
        col3.metric("Avg Files per Client", "6.8")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Clients", "147")
        col2.metric("New Clients", "12")
        col3.metric("Avg Files per Client", "6.8")

    st.markdown("---")


if "page" not in st.session_state:
    st.session_state["page"] = "home"

st.sidebar.title("📚 Menu")
if st.sidebar.button(" Home"):
    st.session_state["page"] = "home"
if st.sidebar.button(" Client Page"):
    st.session_state["page"] = "client"
if st.sidebar.button(" Admin Page"):
    st.session_state["page"] = "admin"



if st.session_state["page"] == "home":
    main()
elif st.session_state["page"] == "client":
    Client_Page.main()
elif st.session_state["page"] == "admin":
    Admin_Page.main()
