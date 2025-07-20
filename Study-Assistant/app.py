from flask import Flask, request, jsonify, abort
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
import os
import json
from dotenv import load_dotenv
import tempfile
import shutil
from flask_cors import CORS
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import numpy as np

# LangChain imports
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:8501", "http://127.0.0.1:8501"], 
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SUPPORTED_FILE_TYPES = [".pdf", ".docx", ".txt"]
MIN_TEXT_LENGTH = 50  # Minimum characters to consider a page has readable text

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx', 'txt'}

def extract_text_with_ocr(pdf_path):
    """Extract text from PDF with fallback to OCR"""
    doc = fitz.open(pdf_path)
    full_text = ""
    
    for page_num in range(len(doc)):
        try:
            page = doc.load_page(page_num)
            
            # 1. First try regular text extraction
            text = ""
            try:
                text = page.get_text("text")  # Explicit text extraction mode
                if len(text.strip()) < MIN_TEXT_LENGTH:
                    raise ValueError("Insufficient text")
                    
            except (AttributeError, ValueError) as e:
                # 2. Fallback to OCR if text extraction fails
                try:
                    pix = page.get_pixmap(dpi=200)  # Higher DPI for better OCR
                    img = Image.open(io.BytesIO(pix.tobytes("ppm")))  # Use PPM format for reliability
                    text = pytesseract.image_to_string(img)
                    text = f"[OCR EXTRACTED]\n{text}\n"  # Mark OCR-derived content
                    
                except Exception as ocr_error:
                    print(f"OCR failed on page {page_num}: {str(ocr_error)}")
                    text = ""  # Skip this page if both methods fail
                    
            full_text += text + "\n\n"
            
        except Exception as page_error:
            print(f"Error processing page {page_num}: {str(page_error)}")
            continue
            
    doc.close()
    return full_text.strip()

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads with OCR support"""
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400
        
    if 'keywords' not in request.form:
        return jsonify({"error": "No keywords provided"}), 400
        
    files = request.files.getlist('files')
    keywords = request.form['keywords']
    
    if not files or all(file.filename == '' for file in files):
        return jsonify({"error": "No selected files"}), 400
    
    documents = []
    temp_dir = tempfile.mkdtemp()
    
    try:
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(temp_dir, filename)
                file.save(filepath)
                
                try:
                    if filename.lower().endswith('.pdf'):
                        # First try regular text extraction
                        try:
                            loader = PyPDFLoader(filepath)
                            docs = loader.load()
                            # If text extraction seems insufficient, try OCR
                            if sum(len(d.page_content) for d in docs) < MIN_TEXT_LENGTH * len(docs):
                                full_text = extract_text_with_ocr(filepath)
                                if full_text.strip():
                                    docs = [Document(page_content=full_text)]
                        except Exception as e:
                            # Fallback to OCR if regular extraction fails
                            full_text = extract_text_with_ocr(filepath)
                            docs = [Document(page_content=full_text)] if full_text.strip() else []
                            
                        documents.extend(docs)
                        
                    elif filename.lower().endswith('.docx'):
                        loader = Docx2txtLoader(filepath)
                        documents.extend(loader.load())
                    elif filename.lower().endswith('.txt'):
                        loader = TextLoader(filepath)
                        documents.extend(loader.load())
                        
                except Exception as e:
                    print(f"Error processing {filename}: {str(e)}")
                    continue
    
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    if not documents:
        return jsonify({"error": "No valid content extracted"}), 400
    
    # Split documents into chunks with better overlap for context
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,  # Increased chunk size for better context
        chunk_overlap=400,  # Increased overlap
        separators=["\n\n", "\n", ". ", " ", ""]  # Better separators
    )
    splits = text_splitter.split_documents(documents)
    
    # Filter out very short chunks and table of contents
    filtered_splits = []
    for doc in splits:
        content = doc.page_content.strip()
        # Filter out table of contents patterns and very short content
        if (len(content) > 100 and 
            not content.count('_') > len(content) * 0.3 and  # Skip lines with too many underscores
            not content.count('.') > len(content) * 0.1):    # Skip lines with too many dots
            filtered_splits.append(doc)
    
    # Combine filtered text content
    full_text = "\n\n".join([doc.page_content for doc in filtered_splits])
    
    print(f"Total text length after filtering: {len(full_text)} characters")
    print(f"First 500 characters: {full_text[:500]}")  # Debug preview
    
    # Create an improved prompt to extract more meaningful information
    prompt_template = """You are an expert document analyzer. Extract comprehensive and meaningful information from the following text based on these keywords: {keywords}

    For each keyword, provide:
    1. **Definition/Description**: What the keyword refers to in this document
    2. **Key Details**: Important facts, requirements, or specifications
    3. **Programs/Courses**: Specific programs, courses, or offerings mentioned
    4. **Requirements**: Any prerequisites, requirements, or conditions
    5. **Additional Context**: Any other relevant information

    Keywords to analyze: {keywords}

    Document Text:
    {text}

    Instructions:
    - Look for substantial content, not just headers or table of contents
    - Extract specific details like course codes, credit hours, requirements, descriptions
    - Include relevant quotes and specific information
    - If a keyword appears in multiple contexts, include all relevant information
    - Focus on actionable and informative content
    - Provide detailed explanations, not just brief mentions

    Return the information in this JSON format:
    {{
      "results": [
        {{
          "keyword": "keyword_name",
          "definition": "What this keyword refers to in the document",
          "key_details": "Important facts and specifications",
          "programs_courses": "Specific programs, courses, or offerings",
          "requirements": "Prerequisites, requirements, or conditions",
          "additional_context": "Other relevant information",
          "relevant_quotes": "Direct quotes from the document"
        }}
      ]
    }}
    
    Return ONLY the JSON structure, nothing else."""
    
    prompt = PromptTemplate.from_template(prompt_template)
    
    chain = (
        {"keywords": RunnablePassthrough(), "text": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )
    
    try:
        # Also try to extract keyword-specific content
        keyword_list = [k.strip() for k in keywords.split(',')]
        
        # For each keyword, find the most relevant chunks
        keyword_specific_content = {}
        for keyword in keyword_list:
            relevant_chunks = []
            for doc in filtered_splits:
                content = doc.page_content.lower()
                if keyword.lower() in content:
                    # Get surrounding context
                    relevant_chunks.append(doc.page_content)
            
            if relevant_chunks:
                # Take the most relevant chunks (up to 3 per keyword)
                keyword_specific_content[keyword] = "\n\n".join(relevant_chunks[:3])
        
        # If we found keyword-specific content, use it; otherwise use full text
        if keyword_specific_content:
            combined_content = "\n\n".join([
                f"=== Content for {keyword} ===\n{content}" 
                for keyword, content in keyword_specific_content.items()
            ])
            analysis_text = combined_content
        else:
            analysis_text = full_text
        
        result = chain.invoke({
            "keywords": keywords,
            "text": analysis_text[:15000]  # Limit to prevent token overflow
        })
        
        # Clean up the response to ensure it's valid JSON
        # Sometimes LLMs add extra text before/after the JSON
        start_idx = result.find('{')
        end_idx = result.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            # If no JSON found, return a structured response
            return jsonify({
                "status": "success",
                "data": {
                    "results": [{
                        "keyword": keywords,
                        "relevant_text": result,
                        "context": "Raw response from model"
                    }]
                }
            })
        
        json_result = result[start_idx:end_idx]
        
        # Parse the JSON to ensure it's valid
        try:
            parsed_json = json.loads(json_result)
            return jsonify({
                "status": "success",
                "data": parsed_json
            })
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON parsing error: {str(e)}")
            # Return a fallback response
            return jsonify({
                "status": "success",
                "data": {
                    "results": [{
                        "keyword": keywords,
                        "relevant_text": result,
                        "context": "Could not parse as JSON, showing raw response"
                    }]
                }
            })
        
    except Exception as e:
        app.logger.error(f"Error processing keywords: {str(e)}")
        return jsonify({
            "error": "Failed to process keywords",
            "details": str(e)
        }), 500

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    return jsonify({
        "message": "Document Information Extractor API",
        "endpoints": {
            "/health": "GET - Health check",
            "/upload": "POST - Upload files and extract information"
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "Service is running"
    })

# Add this test function to your code
def test_ocr_capability():
    test_pdf = "RoomSelectionProcess_SNU.pdf"  # Your test file
    text = extract_text_with_ocr(test_pdf)
    
    print("\n=== OCR TEST RESULTS ===")
    print(f"Total text length: {len(text)} characters")
    print("\nSample extracted text:")
    print(text[:500] + "...")  # Show first 500 chars
    print("\nKey phrases found:")
    for phrase in ["Hostel Management", "Eligibility Criteria", "Room Partner"]:
        print(f"{phrase}: {'FOUND' if phrase in text else 'NOT FOUND'}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)