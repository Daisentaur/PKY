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
    runpy.run_path("frontend/home/ui.py")
elif st.session_state["page"] == "client":
    backend_process = subprocess.Popen(["python", "Client/Client_app.py"])
    
    # Give it time to start (adjust sleep as needed)
    time.sleep(2)  
    
    runpy.run_path("Client/Client_Page.py")
    # Open frontend
    # subprocess.Popen(["streamlit", "run", "Client/Client_Page.py"])
elif st.session_state["page"] == "admin":
    runpy.run_path("frontend/admin/ui.py")




