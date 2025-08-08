import os
from supabase import create_client
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client with type-safe env handling
def get_required_env(var: str) -> str:
    """Get required environment variable or raise error"""
    val = os.getenv(var)
    if not val:
        raise ValueError(f"Missing required environment variable: {var}")
    return val

url = get_required_env("SUPABASE_URL")
key = get_required_env("SUPABASE_KEY")

supabase = create_client(url, key)
TABLE_NAME = "document_sessions"

def create_table():
    """Create the table if it doesn't exist (run once during setup)"""
    # Supabase doesn't support direct table creation via Python client,
    # so you'll need to either:
    # 1. Create manually in Supabase dashboard, OR
    # 2. Run the SQL command below in the SQL editor
    
    # SQL for table creation (run in Supabase SQL editor):
    """
    CREATE TABLE document_sessions (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        session_id UUID NOT NULL UNIQUE,
        config_data JSONB NOT NULL,
        extracted_data JSONB NOT NULL,
        document_metadata JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    
    -- Optional: Add indexes for better query performance
    CREATE INDEX idx_session_id ON document_sessions(session_id);
    CREATE INDEX idx_created_at ON document_sessions(created_at);
    """
    
    # For Python-level table verification:
    try:
        supabase.table(TABLE_NAME).select("*").limit(1).execute()
        print(f"Table {TABLE_NAME} exists")
    except Exception as e:
        print(f"Table {TABLE_NAME} doesn't exist or is inaccessible: {str(e)}")
        print("Create the table using the SQL provided above")

def insert_session(
    session_id: str,
    config_data: Dict[str, Any],
    extracted_data: Dict[str, Any],
    document_metadata: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Insert a new session record"""
    try:
        data = {
            "session_id": session_id,
            "config_data": config_data,
            "extracted_data": extracted_data,
            "document_metadata": document_metadata
        }
        
        response = supabase.table(TABLE_NAME).insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error inserting session: {str(e)}")
        return None

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a session by session_id"""
    try:
        response = supabase.table(TABLE_NAME)\
                         .select("*")\
                         .eq("session_id", session_id)\
                         .single()\
                         .execute()
        return response.data
    except Exception as e:
        print(f"Error retrieving session: {str(e)}")
        return None

def update_extracted_data(session_id: str, extracted_data: Dict[str, Any]) -> bool:
    """Update extracted data for a session"""
    try:
        supabase.table(TABLE_NAME)\
              .update({
                  "extracted_data": extracted_data,
                  "updated_at": datetime.now().isoformat()
              })\
              .eq("session_id", session_id)\
              .execute()
        return True
    except Exception as e:
        print(f"Error updating session: {str(e)}")
        return False

# Initialize table on import (optional)
create_table()