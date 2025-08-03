import re
import hashlib
import magic
from pathlib import Path
from typing import Tuple
from config.settings import Settings

class SecurityValidator:
    """Comprehensive file security checks"""
    
    MALWARE_SIGNATURES = [
        r'<\s*script[^>]*>.*<\s*/\s*script\s*>',
        r'\b(eval|system|exec|passthru)\s*\(',
        r'\b(union\s+select|drop\s+table)\b',
        r'\x00|\xFF|\xFE'  # Binary patterns
    ]
    
    @classmethod
    def validate_file(cls, file_path: str) -> Tuple[bool, str]:
        """Run all security checks"""
        checks = [
            cls._check_extension_mismatch,
            cls._check_malware_patterns,
            cls._check_max_size,
            cls._check_magic_numbers
        ]
        
        for check in checks:
            valid, message = check(file_path)
            if not valid:
                return False, message
                
        return True, "File validated"
    
    @classmethod
    def _check_extension_mismatch(cls, file_path: str) -> Tuple[bool, str]:
        """Verify file content matches extension"""
        ext = Path(file_path).suffix.lower()
        mime = magic.from_file(file_path, mime=True)
        
        mime_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.jpg': 'image/jpeg',
            '.png': 'image/png'
        }
        
        if ext in mime_map and mime != mime_map[ext]:
            return False, f"Extension-MIME mismatch: {ext} != {mime}"
        return True, ""
    
    @classmethod
    def _check_malware_patterns(cls, file_path: str) -> Tuple[bool, str]:
        """Scan for known malicious patterns"""
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
            
            for pattern in cls.MALWARE_SIGNATURES:
                if re.search(pattern, content, re.IGNORECASE):
                    return False, f"Malware pattern detected: {pattern}"
        return True, ""
    
    @classmethod
    def _check_max_size(cls, file_path: str) -> Tuple[bool, str]:
        """Verify file size limits"""
        size = Path(file_path).stat().st_size
        if size > Settings.MAX_FILE_SIZE:
            return False, f"File exceeds {Settings.MAX_FILE_SIZE} byte limit"
        return True, ""
    
    @classmethod
    def _check_magic_numbers(cls, file_path: str) -> Tuple[bool, str]:
        """Verify file headers"""
        valid_headers = {
            b'%PDF-': '.pdf',
            b'\x50\x4B\x03\x04': '.docx',
            b'\xFF\xD8\xFF': '.jpg',
            b'\x89PNG': '.png'
        }
        
        with open(file_path, 'rb') as f:
            header = f.read(4)
            for sig, ext in valid_headers.items():
                if header.startswith(sig):
                    return True, ""
        
        return False, "Invalid file header"