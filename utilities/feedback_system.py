import smtplib
from email.message import EmailMessage
from typing import Dict, Optional
from config.settings import Settings

class FeedbackSystem:
    """Handles user feedback and bug reporting"""
    
    @staticmethod
    def submit_feedback(
        original_output: str,
        edited_output: Optional[str] = None,
        comments: str = "",
        email: Optional[str] = None
    ) -> bool:
        """
        Records feedback and optionally emails it
        Returns success status
        """
        # Store in database (pseudo-code)
        feedback_data = {
            'original': original_output,
            'edited': edited_output,
            'comments': comments,
            'email': email,
            'timestamp': datetime.now().isoformat()
        }
        
        # Database.insert('feedback', feedback_data)  # Connect to your DB
        
        # Email notification if configured
        if Settings.ADMIN_EMAIL:
            return FeedbackSystem._send_email_notification(feedback_data)
        return True
    
    @staticmethod
    def _send_email_notification(data: Dict) -> bool:
        """Internal email sender"""
        try:
            msg = EmailMessage()
            msg.set_content(
                f"New feedback received:\n\n"
                f"Original Output: {data['original'][:500]}...\n\n"
                f"Edited Output: {data['edited'][:500] if data['edited'] else 'None'}\n\n"
                f"Comments: {data['comments']}\n\n"
                f"From: {data.get('email', 'Anonymous')}"
            )
            msg['Subject'] = "Document Analyzer Feedback"
            msg['From'] = Settings.SMTP_USER
            msg['To'] = Settings.ADMIN_EMAIL
            
            with smtplib.SMTP(Settings.SMTP_SERVER, Settings.SMTP_PORT) as server:
                server.starttls()
                server.login(Settings.SMTP_USER, Settings.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False