import os
from supabase import create_client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
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

def create_session(session_id: str, config_data: dict):
    """Create a new session record in database"""
    try:
        data = {
            "session_id": session_id,
            "config_data": config_data,
            "extracted_data": {},
            "document_metadata": {
                "status": "config_uploaded",
                "created_at": datetime.now().isoformat()
            }
        }
        supabase.table(TABLE_NAME).insert(data).execute()
    except Exception as e:
        print(f"Database error creating session: {str(e)}")
        raise

from typing import Optional, Dict, Any

def update_session_record(
    session_id: str, 
    extracted_data: Dict[str, Any], 
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Update session with extracted data"""
    try:
        update_data = {
            "extracted_data": extracted_data,
            "updated_at": datetime.now().isoformat(),
            "document_metadata": {
                "status": "analysis_complete",
                "completed_at": datetime.now().isoformat()
            }
        }
        
        if metadata is not None:  # Explicit check for None
            update_data["document_metadata"].update(metadata)
            
        supabase.table(TABLE_NAME)\
              .update(update_data)\
              .eq("session_id", session_id)\
              .execute()
    except Exception as e:
        print(f"Database error updating session: {str(e)}")
        raise

def get_session(session_id: str):
    """Retrieve a session from database"""
    try:
        response = supabase.table(TABLE_NAME)\
                         .select("*")\
                         .eq("session_id", session_id)\
                         .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Database error getting session: {str(e)}")
        raise