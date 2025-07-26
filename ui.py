import streamlit as st
import requests
from io import BytesIO
import traceback
import xml.etree.ElementTree as ET
import json
import time

# Configuration
BACKEND_URL = "http://127.0.0.1:5001"  # Update if your backend runs on a different port

st.set_page_config(page_title="Document Analyzer", layout="wide")
st.title("📄 Advanced Document Analyzer")
st.markdown("""
    **Two-step document analysis:**  
    1. First upload your configuration file  
    2. Then upload documents for analysis  
""")

# Initialize session state variables
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'config_uploaded' not in st.session_state:
    st.session_state.config_uploaded = False

# Sidebar for configuration
with st.sidebar:
    st.header("Workflow")
    st.markdown("""
    **How to use:**
    1. Upload config file (YAML/JSON)
    2. Upload documents (PDF/DOCX/TXT)
    3. Analyze documents
    4. Download results
    """)
    
    if st.session_state.config_uploaded:
        st.success("✅ Config file uploaded")
        if st.button("Clear Session"):
            st.session_state.clear()
            st.rerun()

# Step 1: Config File Upload
st.subheader("Step 1: Upload Configuration File")
config_file = st.file_uploader(
    "Choose a config file (YAML or JSON)",
    type=["yaml", "yml", "json"],
    key="config_upload",
    disabled=st.session_state.config_uploaded
)

if config_file and not st.session_state.config_uploaded:
    if st.button("Upload Configuration"):
        with st.spinner("Processing config..."):
            try:
                files = {"config_file": (config_file.name, config_file.getvalue())}
                response = requests.post(
                    f"{BACKEND_URL}/upload_config",
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    st.session_state.session_id = response.json().get("session_id")
                    st.session_state.config_uploaded = True
                    st.success("Configuration uploaded successfully!")
                    st.rerun()
                else:
                    st.error(f"Error: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Make sure the Flask app is running.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.code(traceback.format_exc())

# Step 2: Document Upload and Processing
if st.session_state.config_uploaded:
    st.subheader("Step 2: Upload Documents for Analysis")
    uploaded_files = st.file_uploader(
        "Choose documents to analyze",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="doc_upload"
    )
    
    if uploaded_files:
        if st.button("Analyze Documents"):
            with st.spinner("Processing documents..."):
                try:
                    files = [("document_files", (file.name, file.getvalue())) for file in uploaded_files]
                    data = {"session_id": st.session_state.session_id}
                    
                    response = requests.post(
                        f"{BACKEND_URL}/upload_documents",
                        files=files,
                        data=data,
                        timeout=300
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.session_state.extraction_results = result.get("data", {})
                        st.session_state.text_sample = result.get("text_sample", "")
                        st.success("Analysis complete!")
                    else:
                        st.error(f"Error: {response.text}")
                
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to backend. Make sure the Flask app is running.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.code(traceback.format_exc())

# Display results if available
if 'extraction_results' in st.session_state:
    st.subheader("Analysis Results")
    
    # Show text sample preview
    with st.expander("📝 View Document Sample", expanded=False):
        st.text_area("Extracted Text Sample", 
                    st.session_state.text_sample, 
                    height=200)
    
    # Results display format
    st.subheader("Output Options")
    format_col1, format_col2 = st.columns(2)
    
    with format_col1:
        output_format = st.radio(
            "Select output format:",
            ["JSON", "Text", "XML"],
            horizontal=True
        )
    
    with format_col2:
        if st.button("Refresh Results"):
            st.rerun()
    
    # Display results in selected format
    if output_format == "JSON":
        st.json(st.session_state.extraction_results)
    elif output_format == "Text":
        if "results" in st.session_state.extraction_results:
            for item in st.session_state.extraction_results["results"]:
                st.markdown(f"### {item.get('field', 'N/A')}")
                st.markdown(f"**Type:** {item.get('type', 'N/A')}")
                st.markdown(f"**Confidence:** {item.get('confidence', 'N/A')}")
                st.markdown("**Value:**")
                st.write(item.get('value', 'No value extracted'))
                st.divider()
    elif output_format == "XML":
        try:
            root = ET.Element("AnalysisResults")
            if "results" in st.session_state.extraction_results:
                for item in st.session_state.extraction_results["results"]:
                    result_elem = ET.SubElement(root, "Result")
                    ET.SubElement(result_elem, "Field").text = str(item.get('field', ''))
                    ET.SubElement(result_elem, "Type").text = str(item.get('type', ''))
                    ET.SubElement(result_elem, "Confidence").text = str(item.get('confidence', ''))
                    ET.SubElement(result_elem, "Value").text = str(item.get('value', ''))
            
            xml_str = ET.tostring(root, encoding='unicode')
            st.code(xml_str, language="xml")
        except Exception as e:
            st.error(f"Error generating XML: {str(e)}")

    # Download options
    st.subheader("📥 Download Results")
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    
    with dl_col1:
        if st.button("JSON"):
            st.download_button(
                label="Download JSON",
                data=json.dumps(st.session_state.extraction_results, indent=2),
                file_name="analysis_results.json",
                mime="application/json"
            )
    
    with dl_col2:
        if st.button("Text"):
            text_content = ""
            if "results" in st.session_state.extraction_results:
                for item in st.session_state.extraction_results["results"]:
                    text_content += f"Field: {item.get('field', 'N/A')}\n"
                    text_content += f"Type: {item.get('type', 'N/A')}\n"
                    text_content += f"Confidence: {item.get('confidence', 'N/A')}\n"
                    text_content += f"Value: {item.get('value', 'No value extracted')}\n\n"
            
            st.download_button(
                label="Download Text",
                data=text_content,
                file_name="analysis_results.txt",
                mime="text/plain"
            )
    
    with dl_col3:
        if st.button("XML"):
            try:
                root = ET.Element("AnalysisResults")
                if "results" in st.session_state.extraction_results:
                    for item in st.session_state.extraction_results["results"]:
                        result_elem = ET.SubElement(root, "Result")
                        ET.SubElement(result_elem, "Field").text = str(item.get('field', ''))
                        ET.SubElement(result_elem, "Type").text = str(item.get('type', ''))
                        ET.SubElement(result_elem, "Confidence").text = str(item.get('confidence', ''))
                        ET.SubElement(result_elem, "Value").text = str(item.get('value', ''))
                
                xml_str = ET.tostring(root, encoding='unicode')
                st.download_button(
                    label="Download XML",
                    data=xml_str,
                    file_name="analysis_results.xml",
                    mime="application/xml"
                )
            except Exception as e:
                st.error(f"Error generating XML: {str(e)}")

# Session info footer
if st.session_state.config_uploaded:
    st.markdown("---")
    st.caption(f"Active session: `{st.session_state.session_id}`")

st.markdown("---")
st.caption("Document Analyzer")