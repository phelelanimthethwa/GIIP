from flask_mail import Message
from flask import current_app
from models.email_templates import *

class EmailService:
    def __init__(self, mail):
        self.mail = mail

    def send_email(self, to, subject, body):
        """
        Generic email sending function
        """
        try:
            msg = Message(
                subject=subject,
                recipients=[to],
                body=body,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            self.mail.send(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def send_registration_confirmation(self, registration_data):
        """
        Send registration confirmation email
        """
        subject = 'Conference Registration Confirmation'
        body = REGISTRATION_CONFIRMATION.format(
            full_name=registration_data['full_name'],
            registration_type=registration_data['registration_type'],
            currency_symbol=current_app.config.get('CURRENCY_SYMBOL', '$'),
            total_amount=registration_data['total_amount'],
            workshop='Yes' if registration_data.get('workshop') else 'No',
            banquet='Yes' if registration_data.get('banquet') else 'No'
        )
        return self.send_email(registration_data['email'], subject, body)

    def send_paper_confirmation(self, paper_data):
        """
        Send paper submission confirmation email
        """
        subject = 'Paper Submission Confirmation'
        body = PAPER_SUBMISSION_CONFIRMATION.format(
            author_name=paper_data['authors'][0]['name'],
            paper_title=paper_data['paper_title'],
            presentation_type=paper_data['presentation_type'],
            paper_id=paper_data['paper_id']
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