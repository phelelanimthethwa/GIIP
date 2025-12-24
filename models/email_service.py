import resend
from flask import current_app
from models.email_templates import *

class EmailService:
    def __init__(self):
        """Initialize Resend email service"""
        pass
    
    def _get_sender(self):
        """Get the default sender email"""
        return current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@giirconference.com')
    
    def _configure_resend(self):
        """Configure Resend API key"""
        api_key = current_app.config.get('RESEND_API_KEY')
        if not api_key:
            print("Warning: RESEND_API_KEY not configured")
            return False
        resend.api_key = api_key
        return True

    def send_email(self, to, subject, body, html=None):
        """
        Generic email sending function using Resend
        
        Args:
            to: Email recipient (string or list)
            subject: Email subject
            body: Plain text body
            html: Optional HTML body
        """
        try:
            if not self._configure_resend():
                return False
            
            sender = self._get_sender()
            
            # Ensure 'to' is a list
            if isinstance(to, str):
                to = [to]
            
            params = {
                "from": sender,
                "to": to,
                "subject": subject,
                "text": body,
            }
            
            if html:
                params["html"] = html
            
            response = resend.Emails.send(params)
            print(f"Email sent successfully to {to}: {response}")
            return True
            
        except Exception as e:
            print(f"Error sending email via Resend: {str(e)}")
            return False

    def send_registration_confirmation(self, registration_data):
        """
        Send registration confirmation email
        """
        subject = 'Conference Registration Confirmation'
        body = REGISTRATION_CONFIRMATION.format(
            full_name=registration_data['full_name'],
            registration_type=registration_data['registration_type'],
            currency_symbol=current_app.config.get('CURRENCY_SYMBOL', 'R'),
            total_amount=registration_data['total_amount'],
            workshop='Yes' if registration_data.get('workshop') else 'No',
            banquet='Yes' if registration_data.get('banquet') else 'No'
        )
        return self.send_email(registration_data['email'], subject, body)

    def send_paper_confirmation(self, paper_data):
        """
        Send paper submission confirmation email
        """
        conference_name = paper_data.get('conference_name', 'GIIR Conference 2024')
        subject = f'Paper Submission Confirmation - {conference_name}'
        body = PAPER_SUBMISSION_CONFIRMATION.format(
            author_name=paper_data['authors'][0]['name'],
            paper_title=paper_data['paper_title'],
            presentation_type=paper_data['presentation_type'],
            paper_id=paper_data['paper_id'],
            conference_name=conference_name
        )
        return self.send_email(paper_data['user_email'], subject, body)

    def send_paper_status_update(self, paper_data, status, comments=''):
        """
        Send paper status update email
        """
        subject = f'Paper Submission {status.title()}'
        body = PAPER_STATUS_UPDATE[status].format(
            title=paper_data['paper_title'],
            type=paper_data['presentation_type'].replace('_', ' ').title(),
            comments=comments if comments else 'No additional comments provided.'
        )
        return self.send_email(paper_data['user_email'], subject, body)

    def send_welcome_email(self, user_data):
        """
        Send welcome email to newly registered users
        """
        subject = 'Welcome to GIIR Conference 2024'
        body = WELCOME_EMAIL.format(
            full_name=user_data['full_name'],
            email=user_data['email']
        )
        return self.send_email(user_data['email'], subject, body)

    def send_password_reset_email(self, user_data, reset_link):
        """
        Send password reset email
        """
        subject = 'Password Reset - GIIR Conference'
        body = PASSWORD_RESET_EMAIL.format(
            full_name=user_data['full_name'],
            reset_link=reset_link
        )
        return self.send_email(user_data['email'], subject, body)


# Standalone function for direct use
def send_email_resend(recipients, subject, body, html=None):
    """
    Standalone email sending function using Resend
    Can be used without EmailService instance
    """
    try:
        from flask import current_app
        
        api_key = current_app.config.get('RESEND_API_KEY')
        if not api_key:
            print("Warning: RESEND_API_KEY not configured")
            return False
        
        resend.api_key = api_key
        sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@giirconference.com')
        
        # Ensure recipients is a list
        if isinstance(recipients, str):
            recipients = [recipients]
        
        params = {
            "from": sender,
            "to": recipients,
            "subject": subject,
            "text": body,
        }
        
        if html:
            params["html"] = html
        
        response = resend.Emails.send(params)
        print(f"Email sent successfully via Resend: {response}")
        return True
        
    except Exception as e:
        print(f"Error sending email via Resend: {str(e)}")
        return False
