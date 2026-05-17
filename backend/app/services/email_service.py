import os
import logging
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

logger = logging.getLogger(__name__)

# fastapi-mail configuration (credentials handled via env)
mail_conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "placeholder"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "placeholder"),
    MAIL_FROM=os.getenv("MAIL_FROM", "placeholder@example.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_FROM_NAME="Hamnasheen",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_otp_email(email: str, otp: str, purpose: str):
    subject = "Verify your Hamnasheen Account" if purpose == "signup" else "Reset your Hamnasheen Password"
    purpose_text = "verify your new account" if purpose == "signup" else "reset your password"
    
    body = f"""
    <html>
      <body style="font-family: 'DM Sans', sans-serif; background-color: #111111; color: #ffffff; padding: 40px; text-align: center; margin: 0;">
        <div style="max-width: 400px; margin: 0 auto; background: #1A1A1A; padding: 30px; border-radius: 20px; border: 1px solid #2A2A2A; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
          <h2 style="color: #FFC700; font-size: 28px; margin-bottom: 5px;">Ham<em>nasheen</em></h2>
          <div style="width: 24px; height: 1px; background: #FFC700; margin: 15px auto;"></div>
          <p style="font-size: 14px; color: #A0A0A0; line-height: 1.6;">Use the secure verification code below to {purpose_text}.</p>
          <div style="background: #111111; border: 1.5px solid #2A2A2A; border-radius: 12px; padding: 15px; margin: 25px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #FFC700; display: inline-block;">{otp}</span>
          </div>
          <p style="font-size: 11px; color: #444444; letter-spacing: 0.05em; margin-bottom: 0;">This code is temporary and will expire in 5 minutes.</p>
        </div>
      </body>
    </html>
    """
    
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype=MessageType.html
    )
    
    fm = FastMail(mail_conf)
    try:
        await fm.send_message(message)
        logger.info(f"OTP Email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}", exc_info=True)
