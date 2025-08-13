import streamlit as st
import runpy 

st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)


if "page" not in st.session_state:
    st.session_state["page"] = "home"

st.sidebar.title(" Menu")
if st.sidebar.button(" Home"):
    st.session_state["page"] = "home"
if st.sidebar.button(" Client Page"):
    st.session_state["page"] = "client"
if st.sidebar.button(" Admin Page"):
    st.session_state["page"] = "admin"



if st.session_state["page"] == "home":
    runpy.run_path("Home/Home_Page.py")
elif st.session_state["page"] == "client":
    runpy.run_path("Client/app.py")
    time.sleep(3)
    runpy.run_path("Client/ui.py")
elif st.session_state["page"] == "admin":
    runpy.run_path("Admin/Admin_Page.py")

