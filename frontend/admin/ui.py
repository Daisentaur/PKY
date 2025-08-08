import streamlit as st
import pandas as pd
import time
from supabase import create_client
from datetime import datetime
from typing import Optional, Dict, Any

@st.cache_resource
def init_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"Failed to initialize Supabase client: {str(e)}")
        return None

supabase = init_supabase()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'users' not in st.session_state:
    st.session_state.users = [
        {"id": 1, "username": "admin", "email": "admin@client.com", "role": "admin", "status": "active"},
        {"id": 2, "username": "assistant", "email": "assistant@client.com", "role": "assistant", "status": "active"}
    ]

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
        return None

def apply_filters(df, filters):
    """Apply filters to the dataframe"""
    filtered_df = df.copy()
    
   
    if filters.get('id'):
        filtered_df = filtered_df[filtered_df['id'].astype(str).str.contains(filters['id'])]
    
    if filters.get('session_id'):
        filtered_df = filtered_df[filtered_df['session_id'].astype(str).str.contains(
            filters['session_id'], case=False)]
    
    
    if filters.get('config_key') or filters.get('config_value'):
        try:
            config_key = filters.get('config_key', '').lower()
            config_value = filters.get('config_value', '').lower()
            
            filtered_df = filtered_df[
                filtered_df['config_data'].apply(
                    lambda x: (config_key in str(x).lower() and 
                             (not config_value or config_value in str(x).lower()))
                )
            ]
        except Exception as e:
            st.warning(f"Error filtering config data: {str(e)}")
    
    
    if filters.get('metadata_key') or filters.get('metadata_value'):
        try:
            metadata_key = filters.get('metadata_key', '').lower()
            metadata_value = filters.get('metadata_value', '').lower()
            filtered_df = filtered_df[
            filtered_df['document_metadata'].apply(
                lambda x: (metadata_key in str(x).lower() and 
                         (not metadata_value or metadata_value in str(x).lower()))
            )
        ]
        except Exception as e:
            print(f"Error filtering metadata: {e}")

    
    return filtered_df

def database_management():
    st.header("📈 Database Management")
    
    
    df = fetch_document_sessions()
    if df is None:
        return
    if df.empty:
        st.warning("No data found in the database")
        return
    
    
    st.subheader("🔍 Search Records")
    search_term = st.text_input("Search across all fields", key="search_term")
    
    
    st.subheader("🎚️ Filter Records")
    cols = st.columns(3)
    
    filters = {
        'id': cols[0].text_input("Filter by ID", key="filter_id"),
        'session_id': cols[0].text_input("Filter by Session ID", key="filter_session_id"),
        'config_key': cols[1].text_input("Filter by Config Key", key="filter_config_key"),
        'config_value': cols[1].text_input("Filter by Config Value", key="filter_config_value"),
        'metadata_key': cols[2].text_input("Filter by Metadata Key", key="filter_metadata_key"),
        'metadata_value': cols[2].text_input("Filter by Metadata Value", key="filter_metadata_value")
    }
    
    
    filtered_df = apply_filters(df, filters)
    
    
    if search_term:
        search_columns = ['id', 'session_id', 'config_data', 'extracted_data', 'document_metadata']
        mask = pd.concat([filtered_df[col].astype(str).str.contains(search_term, case=False) 
                     for col in search_columns], axis=1).any(axis=1)
        filtered_df = filtered_df[mask]
    
    
    st.subheader("📋 Results")
    
    if filtered_df.empty:
        st.warning("No records match your filters")
    else:
        st.caption(f"Showing {len(filtered_df)} of {len(df)} records")
        
        with st.expander("📊 Tabular View"):
            st.dataframe(filtered_df)
        
        st.subheader("🔍 Column Focus")
        columns_to_show = st.multiselect(
            "Select columns to display",
            options=filtered_df.columns,
            default=['id', 'session_id', 'created_at'],
            key="columns_to_show"
        )
        
        if columns_to_show:
            st.dataframe(filtered_df[columns_to_show])
        
        st.subheader("📄 Record Details")
        selected_index = st.selectbox(
            "Select a record to inspect",
            range(len(filtered_df)),
            format_func=lambda x: f"Record ID: {filtered_df.iloc[x]['id']} (Session: {filtered_df.iloc[x]['session_id'][:8]}...)",
            key="record_selector"
        )
        
        selected_record = filtered_df.iloc[selected_index]
        col1, col2 = st.columns(2)
        
        with col1:
            st.json(selected_record['config_data'])
        
        with col2:
            st.json(selected_record['extracted_data'])
        
        st.json(selected_record['document_metadata'])

def start_page():
    st.title("Admin Login")
    st.write("Please Enter Your Credentials")
    with st.form("Login_Form"):
        username = st.text_input("Username", key="username")
        password = st.text_input("Password", type="password", key="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username == "admin" and password == "admin123":
                st.session_state.authenticated = True
                with st.spinner("Logging in..."):
                    time.sleep(1)
                st.rerun()
            elif username == "assistant" and password == "assistant123":
                st.session_state.authenticated = True
                with st.spinner("Logging in..."):
                    time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid Credentials")

def user_management():
    st.header("👥 User Management")
    df = pd.DataFrame(st.session_state.users)
    st.dataframe(df)
    
    with st.expander("Add New User"):
        with st.form("add_user_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_role = st.selectbox("Role", ["admin", "editor", "assistant"])
            submitted = st.form_submit_button("Add User")
            
            if submitted:
                new_user = {
                    "id": len(st.session_state.users) + 1,
                    "username": new_username,
                    "email": new_email,
                    "role": new_role,
                    "status": "active"
                }
                st.session_state.users.append(new_user)
                st.success("User Added Successfully")
                st.rerun()
def config_file_management():
    st.header("📝 Config File Management")
    
    # Fetch all document sessions
    df = fetch_document_sessions()
    if df is None or df.empty:
        st.warning("No config data available in the database")
        return
    
    # Extract all unique config keys from the database
    try:
        all_config_keys = set()
        for config_data in df['config_data']:
            if isinstance(config_data, dict):
                all_config_keys.update(config_data.keys())
        all_config_keys = sorted(all_config_keys)
    except Exception as e:
        st.error(f"Failed to extract config keys: {str(e)}")
        return
    
    st.subheader("🔍 Select Config to Edit")
    
    # Session selection
    session_options = df['session_id'].unique()
    selected_session = st.selectbox(
        "Select a session",
        options=session_options,
        index=0,
        help="Select the session containing the config you want to edit"
    )
    
    # Get the selected record
    selected_record = df[df['session_id'] == selected_session].iloc[0]
    config_data = selected_record['config_data']
    
    if not isinstance(config_data, dict):
        st.error("Invalid config data format in the selected record")
        return
    
    st.subheader("📋 Current Configuration")
    st.json(config_data)
    
    st.subheader("✏️ Edit Configuration")
    
    # Create editable fields for each config key
    updated_config = {}
    with st.form("config_edit_form"):
        for key in sorted(config_data.keys()):
            current_value = config_data[key]
            
            # Handle different data types appropriately
            if isinstance(current_value, bool):
                updated_value = st.checkbox(key, value=current_value, key=f"config_{key}")
            elif isinstance(current_value, (int, float)):
                updated_value = st.number_input(key, value=current_value, key=f"config_{key}")
            elif isinstance(current_value, str):
                updated_value = st.text_area(key, value=current_value, key=f"config_{key}")
            elif isinstance(current_value, list):
                updated_value = st.text_area(
                    key, 
                    value="\n".join(map(str, current_value)), 
                    help="Enter one item per line for lists",
                    key=f"config_{key}"
                )
                updated_value = [line.strip() for line in updated_value.split("\n") if line.strip()]
            elif isinstance(current_value, dict):
                updated_value = st.text_area(
                    key,
                    value=str(current_value),
                    help="Enter valid JSON for dictionaries",
                    key=f"config_{key}"
                )
                try:
                    updated_value = eval(updated_value) if updated_value else {}
                except:
                    st.warning(f"Invalid format for {key}. Keeping original value.")
                    updated_value = current_value
            else:
                updated_value = st.text_area(key, value=str(current_value), key=f"config_{key}")
            
            updated_config[key] = updated_value
        
        # Add new key option
        st.markdown("---")
        new_key = st.text_input("Add new config key (optional)", key="new_config_key")
        if new_key:
            new_value = st.text_area("Value for new key", key="new_config_value")
            if new_value:
                try:
                    # Try to evaluate as Python literal (for numbers, bools, etc.)
                    updated_config[new_key] = eval(new_value)
                except:
                    # Fall back to string if evaluation fails
                    updated_config[new_key] = new_value
        
        submitted = st.form_submit_button("💾 Save Changes")
    
    if submitted:
        try:
            # Update the record in the database
            update_response = supabase.table("document_sessions").update(
                {"config_data": updated_config}
            ).eq("id", selected_record['id']).execute()
            
            if update_response.data:
                st.success("✅ Config updated successfully!")
                # Refresh the data
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to update config")
        except Exception as e:
            st.error(f"Error updating config: {str(e)}")
    
    st.subheader("⚙️ Advanced Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Config Data"):
            st.rerun()
    
    with col2:
        if st.button("🗑️ Delete This Config", type="secondary"):
            if st.checkbox("Are you sure you want to delete this config?"):
                try:
                    # Set config_data to empty dict
                    delete_response = supabase.table("document_sessions").update(
                        {"config_data": {}}
                    ).eq("id", selected_record['id']).execute()
                    
                    if delete_response.data:
                        st.success("Config cleared successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to clear config")
                except Exception as e:
                    st.error(f"Error clearing config: {str(e)}")

def dashboard():
    st.title("Admin Dashboard")
    st.sidebar.title("Navigation")
    
    menu_options = {
        "Dashboard": "📊",
        "User Management": "👥",
        "DataBase Management": "📈",
        "Config File Management": "📝",
        "Status Check": "⚙️"
    }
    
    menu_option = st.sidebar.radio(
        "Menu",
        list(menu_options.keys()),
        format_func=lambda x: f"{menu_options[x]} {x}"
    )
    
    if menu_option == "Dashboard":
        st.header("📊 Dashboard Overview")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Users", len(st.session_state.users), "5%")
        c2.metric("Active Users", len([u for u in st.session_state.users if u['status'] == 'active']), "-2%")
        c3.metric("Admin Users", len([u for u in st.session_state.users if u['role'] == 'admin']), "0%")
    elif menu_option == "User Management":
        user_management()
    elif menu_option == "DataBase Management":
        database_management()
    elif menu_option == "Config File Management":
        config_file_management()
    elif menu_option == "Status Check":
        st.header("⚙️ Status Check")
        if supabase:
            st.success("✅ Supabase connection active")
        else:
            st.error("❌ Supabase connection failed")
        
        st.metric("Active Sessions", len(st.session_state.users))
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()

def main():
    st.markdown("""
    <style>
        .main { padding-top: 2rem; }
        .sidebar .sidebar-content { padding-top: 2rem; }
        .stButton>button { width: 100%; }
        .stTextInput>div>div>input { padding: 10px; }
        .stDataFrame { width: 100%; }
        .stAlert { padding: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)
    
    if not st.session_state.authenticated:
        start_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()
