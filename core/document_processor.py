import os
import re
import tempfile
import pytesseract
import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from config.settings import Settings
from utilities.error_handler import FileLimitHandler

class DocumentProcessor:
    """Secure document processing with OCR and format support"""
    
    def __init__(self):
        self.processors = {
            '.pdf': self._process_pdf,
            '.docx': self._process_docx,
            '.txt': self._process_text,
            '.png': self._process_image,
            '.jpg': self._process_image,
            '.jpeg': self._process_image,
            '.csv': self._process_csv,
            '.xlsx': self._process_excel
        }
        self.limits = FileLimitHandler()

    def process_batch(self, file_paths: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Process multiple documents with parallel execution
        Returns: {
            "file1.pdf": {
                "content": "extracted text",
                "metadata": {"pages": 5, "format": "pdf"},
                "warnings": []
            }
        }
        """
        results = {}
        with ThreadPoolExecutor(max_workers=Settings.PARALLEL_WORKERS) as executor:
            future_to_file = {
                executor.submit(self._process_single, fp): fp 
                for fp in file_paths
            }
            
            for future in future_to_file:
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results[file_path] = {
                        "content": result[0],
                        "metadata": result[1],
                        "warnings": result[2]
                    }
                except Exception as e:
                    results[file_path] = {
                        "content": "",
                        "metadata": {},
                        "warnings": [f"Processing failed: {str(e)}"]
                    }
        return results

    def _process_single(self, file_path: str) -> Tuple[str, Dict, List[str]]:
        """Secure single document processing pipeline"""
        warnings = []
        
        # File limit checks
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            validation = self.limits.check_page_count(self._get_pdf_page_count(file_path))
            if not validation['valid']:
                warnings.append(validation['message'])

        validation = self.limits.check_file_size(file_path)
        if not validation['valid']:
            warnings.append(validation['message'])

        # Actual processing
        processor = self.processors.get(ext)
        if not processor:
            raise ValueError(f"Unsupported file type: {ext}")

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            try:
                # Secure temp file handling
                tmp_path = tmp.name
                with open(file_path, 'rb') as src:
                    tmp.write(src.read())
                os.chmod(tmp_path, 0o600)  # Restrict permissions

                content = processor(tmp_path)
                metadata = self._generate_metadata(tmp_path, ext)
                
                return (content, metadata, warnings)
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    def _generate_metadata(self, file_path: str, ext: str) -> Dict:
        """Extract document metadata"""
        metadata = {
            "format": ext[1:],  # Remove dot
            "size": os.path.getsize(file_path),
            "created": os.path.getctime(file_path),
            "modified": os.path.getmtime(file_path)
        }
        
        if ext == '.pdf':
            with fitz.Document(file_path) as doc:  # Using Document as you requested
                metadata.update({
                    "pages": len(doc),
                    "author": doc.metadata.get('author'),
                    "title": doc.metadata.get('title')
                })
        elif ext in ('.docx', '.xlsx'):
            metadata["author"] = "N/A"  # Would use python-docx in real impl
        
        return metadata

    def _get_pdf_page_count(self, file_path: str) -> int:
        """Safe PDF page counting"""
        try:
            with fitz.Document(file_path) as doc:  # Using Document
                return len(doc)
        except:
            return 0

    def _process_pdf(self, file_path: str) -> str:
        """PDF processor with OCR fallback"""
        text = ""
        try:
            # Primary text extraction
            with fitz.Document(file_path) as doc:  # Using Document
                for page in doc:
                    text += page.get_text() + "\n\n"
            
            # OCR fallback if text is sparse
            if len(text.strip()) < Settings.MIN_TEXT_LENGTH:
                text = self._run_ocr(file_path)
                
        except Exception as e:
            # Full OCR if PDF is corrupted/image-based
            text = self._run_ocr(file_path)
        
        return self._clean_text(text)

    def _process_docx(self, file_path: str) -> str:
        """DOCX processor"""
        try:
            import docx2txt
            return self._clean_text(docx2txt.process(file_path))
        except ImportError:
            raise RuntimeError("docx2txt package required for DOCX processing")

    def _process_text(self, file_path: str) -> str:
        """Plain text processor"""
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return self._clean_text(f.read())

    def _process_image(self, file_path: str) -> str:
        """Image processor with Tesseract OCR"""
        try:
            return self._clean_text(pytesseract.image_to_string(Image.open(file_path)))
        except pytesseract.TesseractNotFoundError:
            raise RuntimeError("Tesseract OCR not installed. Run: sudo apt install tesseract-ocr")

    def _process_csv(self, file_path: str) -> str:
        """CSV to text conversion"""
        df = pd.read_csv(file_path)
        return self._clean_text(df.to_markdown(index=False))

    def _process_excel(self, file_path: str) -> str:
        """Excel to text conversion"""
        df = pd.read_excel(file_path, engine='openpyxl')
        df = df.dropna(how='all').dropna(axis=1, how='all')
        return self._clean_text(df.to_markdown(index=False))

    def _run_ocr(self, file_path: str) -> str:
        """OCR processing for PDFs"""
        full_text = ""
        with fitz.Document(file_path) as doc:  # Using Document
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img)
                full_text += f"[OCR Page {page.number}]\n{text}\n\n"
        return full_text

    def _clean_text(self, text: str) -> str:
        """Text normalization and cleaning"""
        # Remove non-printable chars
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove scanner artifacts
        text = re.sub(r'(?m)^\s*[\-_]+\s*$', '', text)
        
        return text