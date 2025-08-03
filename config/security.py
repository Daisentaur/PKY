from config.settings import Settings
import hashlib
import hmac

class SecurityManager:
    """Handles encryption and access control"""
    
    @staticmethod
    def generate_secure_token(payload: str) -> str:
        """Create HMAC-secured token"""
        return hmac.new(
            Settings.SUPABASE_KEY.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def validate_token(token: str, payload: str) -> bool:
        """Verify token integrity"""
        expected = SecurityManager.generate_secure_token(payload)
        return hmac.compare_digest(token, expected)
    
    @staticmethod
    def hash_content(content: bytes) -> str:
        """Generate file content hash"""
        return hashlib.sha256(content).hexdigest()