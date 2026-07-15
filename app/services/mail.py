from flask import current_app
from flask_mail import Message
from app.extensions import mail

def send_verification_email(to_email, first_name, token):
    frontend_url = current_app.config.get('FRONTEND_URL')
    verify_url = f"{frontend_url}/verify-email?token={token}"
    
    subject = "Verify your Linkly Account"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <h2 style="color: #0f172a; font-size: 24px; font-weight: 700; margin-top: 0; margin-bottom: 16px;">Welcome to Linkly!</h2>
        <p style="color: #334155; font-size: 16px; line-height: 24px; margin-bottom: 24px;">
            Hi {first_name},<br><br>
            Thank you for signing up for Linkly—your smart URL management platform. Please verify your email address to activate your account and start shortening links.
        </p>
        <div style="text-align: center; margin-bottom: 24px;">
            <a href="{verify_url}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Verify Email Address</a>
        </div>
        <p style="color: #64748b; font-size: 14px; line-height: 20px;">
            If the button doesn't work, copy and paste this URL into your web browser:<br>
            <a href="{verify_url}" style="color: #2563eb; word-break: break-all;">{verify_url}</a>
        </p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;">
        <p style="color: #94a3b8; font-size: 12px; text-align: center; margin: 0;">
            © 2026 Linkly. Designed & Developed by Rishi
        </p>
    </div>
    """

    if current_app.config.get('MAIL_SUPPRESS_SEND') or not current_app.config.get('MAIL_USERNAME'):
        current_app.logger.info("=========================================")
        current_app.logger.info(f"MOCK EMAIL SENT TO: {to_email}")
        current_app.logger.info(f"SUBJECT: {subject}")
        current_app.logger.info(f"VERIFY LINK: {verify_url}")
        current_app.logger.info("=========================================")
        return True

    try:
        msg = Message(
            subject=subject,
            recipients=[to_email],
            html=html_content
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {e}")
        return False

def send_password_reset_email(to_email, first_name, token):
    frontend_url = current_app.config.get('FRONTEND_URL')
    reset_url = f"{frontend_url}/reset-password?token={token}"
    
    subject = "Reset your Linkly Password"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <h2 style="color: #0f172a; font-size: 24px; font-weight: 700; margin-top: 0; margin-bottom: 16px;">Password Reset Request</h2>
        <p style="color: #334155; font-size: 16px; line-height: 24px; margin-bottom: 24px;">
            Hi {first_name},<br><br>
            We received a request to reset the password for your Linkly account. Click the button below to choose a new password. This link will expire in 1 hour.
        </p>
        <div style="text-align: center; margin-bottom: 24px;">
            <a href="{reset_url}" style="background-color: #2563eb; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">Reset Password</a>
        </div>
        <p style="color: #64748b; font-size: 14px; line-height: 20px;">
            If the button doesn't work, copy and paste this URL into your web browser:<br>
            <a href="{reset_url}" style="color: #2563eb; word-break: break-all;">{reset_url}</a>
        </p>
        <p style="color: #64748b; font-size: 14px; line-height: 20px; margin-top: 16px;">
            If you did not request a password reset, you can safely ignore this email.
        </p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0;">
        <p style="color: #94a3b8; font-size: 12px; text-align: center; margin: 0;">
            © 2026 Linkly. Designed & Developed by Rishi
        </p>
    </div>
    """

    if current_app.config.get('MAIL_SUPPRESS_SEND') or not current_app.config.get('MAIL_USERNAME'):
        current_app.logger.info("=========================================")
        current_app.logger.info(f"MOCK PASSWORD RESET EMAIL SENT TO: {to_email}")
        current_app.logger.info(f"SUBJECT: {subject}")
        current_app.logger.info(f"RESET LINK: {reset_url}")
        current_app.logger.info("=========================================")
        return True

    try:
        msg = Message(
            subject=subject,
            recipients=[to_email],
            html=html_content
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {e}")
        return False
