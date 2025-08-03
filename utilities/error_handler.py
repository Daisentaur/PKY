import os
from pathlib import Path
from typing import Dict, Union
from config.settings import Settings

class FileLimitHandler:
    """Handles all file size and format validations"""
    
    @staticmethod
    def check_page_count(page_count: int) -> Dict[str, Union[bool, str]]:
        """Validate PDF page limits"""
        if page_count > Settings.MAX_PAGES:
            return {
                'valid': False,
                'message': (
                    f"Document exceeds {Settings.MAX_PAGES} page limit. "
                    f"Please split your {page_count}-page document into "
                    "chunks under {Settings.MAX_PAGES} pages each."
                )
            }
        return {'valid': True, 'message': ""}
    
    @staticmethod
    def check_file_size(file_path: str) -> Dict[str, Union[bool, str]]:
        """Validate file size limits"""
        size = Path(file_path).stat().st_size
        if size > Settings.MAX_FILE_SIZE:
            return {
                'valid': False,
                'message': (
                    f"File exceeds {Settings.MAX_FILE_SIZE/1024/1024}MB limit. "
                    f"Actual size: {size/1024/1024:.2f}MB"
                )
            }
        return {'valid': True, 'message': ""}

    @staticmethod
    def validate_extension(filename: str) -> bool:
        """Check against allowed extensions"""
        return Path(filename).suffix.lower() in Settings.ALLOWED_EXTENSIONS