import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

class Settings:
    """Central configuration for all modules"""
    
    # API Keys
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_URL = os.getenv('OPENROUTER_URL', "https://openrouter.ai/api/v1/chat/completions")

    # OpenRouter Configuration
    OPENROUTER_MODEL = ""  
    
    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # Processing Limits
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB
    MIN_TEXT_LENGTH = 50 
    MAX_PAGES = int(os.getenv('MAX_PAGES', 800))
    PARALLEL_WORKERS = int(os.getenv('PARALLEL_WORKERS', 4))
    MAX_MEMORY = int(os.getenv('MAX_MEMORY', 1 * 1024 * 1024 * 1024))  # 1GB
    
    # Security
    ALLOWED_EXTENSIONS = [
        '.pdf', '.docx', '.txt',
        '.png', '.jpg', '.jpeg',
        '.csv', '.xlsx'
    ]

    @classmethod
    def verify(cls):
        """Validate critical configurations"""
        required = [
            'OPENROUTER_API_KEY',
            'SUPABASE_URL', 
            'SUPABASE_KEY'
        ]
        missing = [var for var in required if not getattr(cls, var)]
        if missing:
            raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")

# Validate on import
Settings.verify()