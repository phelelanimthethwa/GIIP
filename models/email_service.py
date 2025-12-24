import resend
from flask import current_app
from models.email_templates import *
import time
from typing import List, Dict, Optional

class EmailService:
    def __init__(self):
        """Initialize Resend email service"""
        self.batch_size = 50  # Resend allows up to 100 emails per batch
        self.rate_limit_delay = 0.1  # Small delay between batches to avoid rate limiting
    
    def _get_sender(self):
        """Get the default sender email"""
        return current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@globalconference.co.za')
    
    def _configure_resend(self):
        """Configure Resend API key"""
        api_key = current_app.config.get('RESEND_API_KEY')
        if not api_key:
            print("Warning: RESEND_API_KEY not configured")
            return False
        resend.api_key = api_key
        return True
    
    def _get_conference_url(self):
        """Get the conference website URL"""
        return current_app.config.get('CONFERENCE_URL', 'https://globalconference.co.za')

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

    def send_announcement_email(self, recipients: List[str], announcement_data: Dict) -> Dict:
        """
        Send announcement email to multiple recipients using Resend batch API
        
        Args:
            recipients: List of email addresses
            announcement_data: Dictionary containing announcement details:
                - title: Announcement title
                - content: HTML content
                - type: Announcement type (important, info, event, update)
                - scheduled_date: Date string
                - scheduled_time: Time string
                - timezone: Timezone string
                - image_url: Optional image URL
        
        Returns:
            Dictionary with status and details
        """
        try:
            if not self._configure_resend():
                return {
                    'success': False,
                    'error': 'Resend API key not configured',
                    'sent_count': 0,
                    'failed_count': len(recipients)
                }
            
            if not recipients:
                return {
                    'success': False,
                    'error': 'No recipients provided',
                    'sent_count': 0,
                    'failed_count': 0
                }
            
            sender = self._get_sender()
            conference_url = self._get_conference_url()
            
            # Get type badge
            type_badge = ANNOUNCEMENT_TYPE_BADGES.get(
                announcement_data.get('type', 'info'),
                '📋 Information'
            )
            
            # Build image section if image exists
            image_section = ''
            if announcement_data.get('image_url'):
                image_url = announcement_data['image_url']
                # Make URL absolute if it's relative
                if image_url.startswith('/'):
                    image_url = f"{conference_url}{image_url}"
                image_section = f'''
                    <div style="margin-bottom: 24px; border-radius: 12px; overflow: hidden;">
                        <img src="{image_url}" alt="Announcement Image" style="width: 100%; height: auto; display: block;">
                    </div>
                '''
            
            # Format the HTML email
            html_content = ANNOUNCEMENT_EMAIL_HTML.format(
                title=announcement_data.get('title', 'Announcement'),
                content=announcement_data.get('content', ''),
                type_badge=type_badge,
                scheduled_date=announcement_data.get('scheduled_date', ''),
                scheduled_time=announcement_data.get('scheduled_time', ''),
                timezone=announcement_data.get('timezone', 'UTC'),
                image_section=image_section,
                conference_url=conference_url,
                unsubscribe_url=f"{conference_url}/profile#email-preferences"
            )
            
            # Format plain text email
            text_content = ANNOUNCEMENT_EMAIL_TEXT.format(
                title=announcement_data.get('title', 'Announcement'),
                content=self._strip_html(announcement_data.get('content', '')),
                scheduled_date=announcement_data.get('scheduled_date', ''),
                scheduled_time=announcement_data.get('scheduled_time', ''),
                timezone=announcement_data.get('timezone', 'UTC'),
                announcement_type=announcement_data.get('type', 'info').title()
            )
            
            subject = f"[GIIR Conference] {announcement_data.get('title', 'Announcement')}"
            
            # Send emails in batches using Resend's batch API
            sent_count = 0
            failed_count = 0
            errors = []
            
            # Split recipients into batches
            for i in range(0, len(recipients), self.batch_size):
                batch = recipients[i:i + self.batch_size]
                
                try:
                    # Create batch of emails
                    emails_batch = []
                    for recipient in batch:
                        emails_batch.append({
                            "from": sender,
                            "to": [recipient],
                            "subject": subject,
                            "html": html_content,
                            "text": text_content
                        })
                    
                    # Send batch using Resend
                    response = resend.Batch.send(emails_batch)
                    print(f"[EMAIL] Batch sent: {len(batch)} emails, response: {response}")
                    sent_count += len(batch)
                    
                    # Small delay to avoid rate limiting
                    if i + self.batch_size < len(recipients):
                        time.sleep(self.rate_limit_delay)
                        
                except Exception as batch_error:
                    print(f"[EMAIL] Batch error: {str(batch_error)}")
                    failed_count += len(batch)
                    errors.append(str(batch_error))
            
            return {
                'success': sent_count > 0,
                'sent_count': sent_count,
                'failed_count': failed_count,
                'total_recipients': len(recipients),
                'errors': errors if errors else None
            }
            
        except Exception as e:
            print(f"[EMAIL] Error sending announcement emails: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'sent_count': 0,
                'failed_count': len(recipients) if recipients else 0
            }
    
    def _strip_html(self, html_content: str) -> str:
        """Strip HTML tags from content for plain text version"""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Convert HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        return text

    def send_announcement_to_users(self, users_ref, announcement_data: Dict) -> Dict:
        """
        Fetch all users from Firebase and send announcement email
        
        Args:
            users_ref: Firebase reference to users collection
            announcement_data: Announcement data dictionary
            
        Returns:
            Dictionary with email sending status
        """
        try:
            users = users_ref.get()
            if not users:
                return {
                    'success': False,
                    'error': 'No users found in database',
                    'sent_count': 0,
                    'failed_count': 0
                }
            
            # Extract emails from users, respecting email preferences
            recipients = []
            for user_id, user_data in users.items():
                if user_data.get('email'):
                    # Check email preferences - skip if user opted out of announcements
                    email_prefs = user_data.get('email_preferences', {})
                    if email_prefs.get('announcements', True):  # Default to True if not set
                        recipients.append(user_data['email'])
            
            print(f"[EMAIL] Found {len(recipients)} recipients who opted in for announcements")
            
            if not recipients:
                return {
                    'success': False,
                    'error': 'No users with email opted in for announcements',
                    'sent_count': 0,
                    'failed_count': 0
                }
            
            return self.send_announcement_email(recipients, announcement_data)
            
        except Exception as e:
            print(f"[EMAIL] Error fetching users for announcement: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'sent_count': 0,
                'failed_count': 0
            }


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
        sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@globalconference.co.za')
        
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
