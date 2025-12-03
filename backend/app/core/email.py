import smtplib
import random
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    """Generate a secure 6-digit OTP."""
    return str(random.randint(100000, 999999))


def send_otp_email(email: str, otp_code: str) -> bool:
    """
    Send OTP verification email via SMTP.
    Returns True if sent successfully, False otherwise.
    
    In development mode (when SMTP not configured), logs OTP to console.
    """
    smtp_username = getattr(settings, 'SMTP_USERNAME', None)
    smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
    
    # Check if SMTP is configured (not empty strings)
    if not smtp_username or not smtp_password or smtp_username == "" or smtp_password == "":
        # Development mode: log OTP to console instead of sending email
        message = f"""
{'='*60}
DEVELOPMENT MODE: Email verification code
{'='*60}
Email: {email}
OTP Code: {otp_code}
This code expires in 10 minutes
{'='*60}
"""
        print(message, flush=True)
        # Return True in dev mode so registration can proceed
        return True
    
    try:
        smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = getattr(settings, 'SMTP_PORT', 587)
        from_email = getattr(settings, 'SMTP_FROM_EMAIL', smtp_username)
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = email
        msg['Subject'] = "Verify your email - Intentional Social"
        
        # Email body
        body = f"""Hello,

Please use this code to verify your email address:

{otp_code}

This code will expire in 10 minutes.

If you didn't request this, please ignore this email.

Best,
Intentional Social
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"OTP email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        return False

