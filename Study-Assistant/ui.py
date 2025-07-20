import streamlit as st
import requests
from io import BytesIO
import traceback
import xml.etree.ElementTree as ET
import json

# Configuration - FIXED: Changed port to match backend
BACKEND_URL = "http://127.0.0.1:5001"

st.title("📄 Document Information Extractor")
st.markdown("Upload files and enter keywords to extract structured information")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    st.markdown("""
    **How to use:**
    1. Upload one or more files (PDF, DOCX, TXT)
    2. Enter comma-separated keywords
    3. Click 'Extract Information'
    4. Choose your preferred output format
    """)

# Main content area
uploaded_files = st.file_uploader(
    "Choose files", 
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True
)

keywords = st.text_input(
    "Keywords (comma separated)", 
    placeholder="e.g., sequence, geometric, mathematics"
)

if st.button("Extract Information"):
    if not uploaded_files:
        st.warning("Please upload at least one file")
    elif not keywords:
        st.warning("Please enter some keywords")
    else:
        with st.spinner("Processing files..."):
            try:
                # Prepare the request
                files = [("files", (file.name, file.getvalue())) for file in uploaded_files]
                data = {"keywords": keywords}
                
                # Send to Flask backend
                response = requests.post(
                    f"{BACKEND_URL}/upload",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success("Extraction complete!")
                    
                    # Store results in session state
                    st.session_state.extraction_results = result.get("data", {})
                    
                else:
                    st.error(f"Error: {response.text}")
            
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Make sure the Flask app is running on port 5001.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.code(traceback.format_exc())

# Display format selection if results exist
if 'extraction_results' in st.session_state:
    st.subheader("Output Options")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("View as JSON"):
            st.session_state.output_format = "json"
    with col2:
        if st.button("View as Text"):
            st.session_state.output_format = "text"
    with col3:
        if st.button("View as XML"):
            st.session_state.output_format = "xml"
    
    # Display based on selected format
    if 'output_format' in st.session_state:
        st.subheader("Extracted Information")
        
        if st.session_state.output_format == "json":
            st.json(st.session_state.extraction_results)
            
        elif st.session_state.output_format == "text":
            if "results" in st.session_state.extraction_results:
                for item in st.session_state.extraction_results["results"]:
                    st.markdown(f"### {item.get('keyword', 'N/A')}")
                    for field in ['definition', 'key_details', 'programs_courses', 
                                'requirements', 'relevant_quotes', 'additional_context']:
                        if item.get(field):
                            st.markdown(f"**{field.replace('_', ' ').title()}:**")
                            st.write(item[field])
                            st.write("")
            
        elif st.session_state.output_format == "xml":
            try:
                # Convert JSON to XML
                root = ET.Element("ExtractionResults")
                if "results" in st.session_state.extraction_results:
                    for item in st.session_state.extraction_results["results"]:
                        result_elem = ET.SubElement(root, "Result")
                        ET.SubElement(result_elem, "Keyword").text = str(item.get('keyword', ''))
                        for field in ['definition', 'key_details', 'programs_courses',
                                     'requirements', 'relevant_quotes', 'additional_context']:
                            if item.get(field):
                                ET.SubElement(result_elem, field.replace('_', '')).text = str(item[field])
                
                xml_str = ET.tostring(root, encoding='unicode')
                st.code(xml_str, language="xml")
            except Exception as e:
                st.error(f"Error generating XML: {str(e)}")

# Footer
st.markdown("---")
st.caption("Document Information Extractor - Powered by LangChain and Streamlit")