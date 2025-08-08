import os
from typing import Union,Optional, Dict, Any
import json
import yaml
import uuid
import tempfile
import shutil
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, abort
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from flask_cors import CORS
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import pandas as pd
import requests
from supabase import create_client
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:8501", "http://127.0.0.1:8501"], 
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Configuration
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 400
SUPPORTED_DOC_TYPES = [".pdf", ".docx", ".txt", ".xlsx", ".csv"]
SUPPORTED_CONFIG_TYPES = [".yaml", ".yml", ".json"]
MIN_TEXT_LENGTH = 50
MAX_CONFIG_SIZE = 1 * 1024 * 1024  # 1MB
SESSION_EXPIRE_HOURS = 2

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

# In-memory session store (now used as cache alongside database)
sessions = {}

# Database Operations
def create_session_record(session_id: str, config_data: dict):
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

def get_session_record(session_id: str):
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

# Helper Functions (unchanged from your original)
def allowed_document_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx', 'txt', 'xlsx', 'csv'}

def allowed_config_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'yaml', 'yml', 'json'}

def extract_text_with_ocr(pdf_path):
    """Extract text from PDF with fallback to OCR"""
    doc = fitz.open(pdf_path)
    full_text = ""

    for page_num in range(len(doc)):
        try:
            page = doc.load_page(page_num)
            text = page.get_text("text")
            if len(text.strip()) < MIN_TEXT_LENGTH:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("ppm")))
                text = pytesseract.image_to_string(img)
                text = f"[OCR EXTRACTED]\n{text}\n"
                
            full_text += text + "\n\n"
            
        except Exception as e:
            continue
            
    doc.close()
    return full_text.strip()

def parse_config_file(file):
    """Parse and validate config file"""
    try:
        # Check file size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_CONFIG_SIZE:
            raise ValueError(f"Config file exceeds {MAX_CONFIG_SIZE/1024/1024}MB limit")
        
        # Secure temporary file handling
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            with open(tmp.name, 'r') as f:
                if file.filename.lower().endswith('.json'):
                    config = json.load(f)
                else:
                    config = yaml.safe_load(f)
                
                # Validate config structure
                if not isinstance(config, dict):
                    raise ValueError("Config must be a dictionary")
                
                if 'fields' not in config:
                    raise ValueError("Config must contain 'fields' key")
                
                if not isinstance(config['fields'], list):
                    raise ValueError("Fields must be a list")
                
                # Validate each field
                for field in config['fields']:
                    if not isinstance(field, dict):
                        raise ValueError("Each field must be a dictionary")
                    if 'keywords' not in field:
                        raise ValueError("Field missing 'keywords' list")
                    
                return config
                
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid config format: {str(e)}")
    except Exception as e:
        raise ValueError(f"Config processing error: {str(e)}")

def query_gemini(prompt: str, session_id: Union[str, None] = None) -> str:
    """Call Google Gemini API with the given prompt"""
    try:
        # Initialize the model with proper typing
        model = ChatGoogleGenerativeAI(model='gemini-2.0-flash')
        # Get response with type checking
        response = model.invoke(prompt)
        
        # Handle different response types
        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, list):
            # Convert list responses to string
            return "\n".join(str(item) for item in response.content)
        else:
            return str(response.content)
            
    except Exception as e:
        raise ValueError(f"Gemini API error: {str(e)}")

def build_dynamic_prompt(fields, text):
    """Generate analysis prompt based on fields"""
    fields_section = "\n".join(
        f"- {field.get('name', f'field_{i+1}')}: "
        f"Keywords: {', '.join(field.get('keywords', []))}\n"
        f"  Response type: {field.get('response_type', 'auto')}\n"
        f"  Description: {field.get('description', 'N/A')}"
        for i, field in enumerate(fields)
    )
    
    return f"""Analyze this document and extract information:

FIELDS TO EXTRACT:
{fields_section}

DOCUMENT CONTENT:
{text[:15000]}

INSTRUCTIONS:
1. For each field, determine appropriate response format:
   - Concise: For IDs, numbers, simple facts
   - Detailed: For policies, conditions
2. Return JSON with this structure:
{{
  "results": [
    {{
      "field": "field_name",
      "value": "extracted_value",
      "type": "concise/detailed",
      "confidence": 0.0-1.0
      "source-location" : Page X, section Y 
    }}
  ]
}}

OUTPUT:"""

# API Endpoints with Database Integration
@app.route('/upload_config', methods=['POST'])
def upload_config():
    """First step: Upload configuration file"""
    if 'config_file' not in request.files:
        abort(400, "No config file uploaded")
    
    config_file = request.files['config_file']
    if not config_file.filename or not allowed_config_file(config_file.filename):
        abort(400, "Invalid config file type")
    
    try:
        config = parse_config_file(config_file)
        session_id = str(uuid.uuid4())
        expiry = datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)
        
        # Create in both memory cache and database
        sessions[session_id] = {
            "config": config,
            "expiry": expiry
        }
        create_session_record(session_id, config)
        
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "expires_at": expiry.isoformat()
        })
    except ValueError as e:
        abort(400, str(e))

@app.route('/upload_documents', methods=['POST'])
def upload_documents():
    """Second step: Upload documents and process with config"""
    # Validate session
    if 'session_id' not in request.form:
        abort(400, "Session ID required")
    
    session_id = request.form['session_id']
    
    # Check both cache and database
    session_data = sessions.get(session_id)
    if not session_data:
        session_data = get_session_record(session_id)
        if not session_data:
            abort(400, "Invalid session ID")
        sessions[session_id] = {
            "config": session_data['config_data'],
            "expiry": datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)
        }
    
    if datetime.now() > sessions[session_id]['expiry']:
        abort(400, "Expired session ID")
    
    config = sessions[session_id]['config']
    
    # Validate documents
    if 'document_files' not in request.files:
        abort(400, "No documents uploaded")
    
    document_files = request.files.getlist('document_files')
    if not document_files or all(f.filename == '' for f in document_files):
        abort(400, "No selected files")
    
    # Process documents
    documents = []
    temp_dir = tempfile.mkdtemp()
    file_metadata = {
        "file_names": [],
        "file_types": [],
        "file_sizes": []
    }
    
    try:
        for file in document_files:
            if not file or not file.filename or not allowed_document_file(file.filename):
                continue
                
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(temp_dir, filename)
                file.save(filepath)
                
                # Track metadata
                file_metadata["file_names"].append(filename)
                file_metadata["file_types"].append(filename.split('.')[-1].lower())
                file_metadata["file_sizes"].append(os.path.getsize(filepath))
                
                # Process based on file type
                if filename.lower().endswith('.pdf'):
                    try:
                        loader = PyPDFLoader(filepath)
                        docs = loader.load()
                        if sum(len(d.page_content) for d in docs) < MIN_TEXT_LENGTH * len(docs):
                            full_text = extract_text_with_ocr(filepath)
                            if full_text.strip():
                                docs = [Document(page_content=full_text)]
                    except Exception as e:
                        full_text = extract_text_with_ocr(filepath)
                        docs = [Document(page_content=full_text)] if full_text.strip() else []
                        
                    documents.extend(docs)
                    
                elif filename.lower().endswith('.docx'):
                    loader = Docx2txtLoader(filepath)
                    documents.extend(loader.load())
                elif filename.lower().endswith('.txt'):
                    loader = TextLoader(filepath)
                    documents.extend(loader.load())
                elif filename.lower().endswith('.csv'):
                    df = pd.read_csv(filepath)
                    content = df.to_markdown(index=False)
                    docs = [Document(page_content=content, metadata={"source": filename})]
                    documents.extend(docs)

                elif filename.lower().endswith('.xlsx'):
                    df = pd.read_excel(filepath, engine='openpyxl')
                    df.dropna(how='all', inplace=True)
                    df.dropna(axis=1, how='all', inplace=True)

                    if not df.empty:
                        try:
                            content = df.to_markdown(index=False)
                        except ImportError:
                            content = df.to_string(index=False)

                        docs = [Document(page_content=content)]
                        documents.extend(docs)
                    
            except Exception as e:
                continue
    
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    if not documents:
        abort(400, "No valid content extracted from documents")
    
    # Process text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    splits = text_splitter.split_documents(documents)
    
    # Filter out noise
    filtered_splits = []
    for doc in splits:
        content = doc.page_content.strip()
        if (len(content) > 100 and 
            not content.count('_') > len(content) * 0.3 and
            not content.count('.') > len(content) * 0.1):
            filtered_splits.append(doc)
    
    full_text = "\n\n".join([doc.page_content for doc in filtered_splits])
    
    # Generate and process prompt
    try:
        prompt = build_dynamic_prompt(config['fields'], full_text)
        llm_response = query_gemini(prompt, session_id)
        
        # Extract JSON from response
        start_idx = llm_response.find('{')
        end_idx = llm_response.rfind('}') + 1
        json_result = llm_response[start_idx:end_idx]
        
        try:
            parsed = json.loads(json_result)
            
            # Update database with results
            update_session_record(
                session_id=session_id,
                extracted_data=parsed,
                metadata={
                    "file_count": len(file_metadata["file_names"]),
                    "file_types": list(set(file_metadata["file_types"])),
                    "processing_time": str(datetime.now() - sessions[session_id]['expiry'] + timedelta(hours=SESSION_EXPIRE_HOURS))
                }
            )
            
            return jsonify({
                "status": "success",
                "data": parsed,
                "text_sample": full_text[:500] + "..." if len(full_text) > 500 else full_text
            })
        except json.JSONDecodeError:
            return jsonify({
                "status": "partial_success",
                "raw_response": llm_response,
                "message": "Could not parse LLM response as JSON"
            })
            
    except Exception as e:
        abort(500, f"Analysis failed: {str(e)}")

@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Check session status"""
    # Check both cache and database
    session_data = sessions.get(session_id)
    if not session_data:
        session_data = get_session_record(session_id)
        if not session_data:
            abort(404, "Session not found")
        
        sessions[session_id] = {
            "config": session_data['config_data'],
            "expiry": datetime.fromisoformat(session_data['document_metadata']['created_at']) + timedelta(hours=SESSION_EXPIRE_HOURS)
        }
    
    return jsonify({
        "status": "active",
        "expires_at": sessions[session_id]['expiry'].isoformat(),
        "fields": [f['name'] for f in sessions[session_id]['config']['fields']]
    })

@app.route('/session_data/<session_id>', methods=['GET'])
def get_session_data(session_id):
    """Get complete session data from database"""
    try:
        session_data = get_session_record(session_id)
        if not session_data:
            abort(404, "Session not found in database")
        return jsonify(session_data)
    except Exception as e:
        abort(500, f"Error retrieving session data: {str(e)}")

@app.route('/')
def home():
    return jsonify({
        "message": "Document Analysis API",
        "endpoints": {
            "/upload_config": "POST - Upload configuration",
            "/upload_documents": "POST - Upload documents with session_id",
            "/session/<id>": "GET - Check session status",
            "/session_data/<id>": "GET - Get full session data",
            "/health": "GET - Service health"
        }
    })

@app.route('/health')
def health_check():
    # Verify database connection
    try:
        supabase.table(TABLE_NAME).select("*").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(sessions),
        "database": db_status
    })

if __name__ == '__main__':
    # Verify Tesseract installation
    try:
        pytesseract.get_tesseract_version()
    except EnvironmentError:
        print("Warning: Tesseract OCR not installed")
    
    app.run(host='0.0.0.0', port=5001, debug=True)