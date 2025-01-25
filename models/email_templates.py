REGISTRATION_CONFIRMATION = """
Dear {full_name},

Thank you for registering for GIIR Conference 2024!

Registration Details:
- Registration Type: {registration_type}
- Total Amount: {currency_symbol}{total_amount}
- Workshop: {workshop}
- Banquet: {banquet}

Please keep this email for your records.

Best regards,
GIIR Conference Team
"""

PAPER_SUBMISSION_CONFIRMATION = """
Dear {author_name},

Thank you for submitting your paper to GIIR Conference 2024.

Submission Details:
- Paper Title: {paper_title}
- Presentation Type: {presentation_type}
- Submission ID: {paper_id}

We will review your submission and get back to you soon.

Best regards,
GIIR Conference Team
"""

PAPER_STATUS_UPDATE = {
    'accepted': """
Congratulations! Your paper has been accepted for the GIIR Conference 2024.

Paper Details:
Title: {title}
Presentation Type: {type}

Please prepare your presentation according to the conference guidelines.
{comments}

Best regards,
GIIR Conference Team
""",
    'rejected': """
Thank you for submitting your paper to the GIIR Conference 2024.

We regret to inform you that your paper was not accepted for presentation.

Paper Details:
Title: {title}
Presentation Type: {type}

Review Comments:
{comments}

We encourage you to consider our feedback for future submissions.

Best regards,
GIIR Conference Team
""",
    'revision': """
Thank you for submitting your paper to the GIIR Conference 2024.

Your paper requires revisions before it can be accepted.

Paper Details:
Title: {title}
Presentation Type: {type}

Review Comments:
{comments}

Please submit your revised version through the conference system.

Best regards,
GIIR Conference Team
"""
}

WELCOME_EMAIL = """
Dear {full_name},

Welcome to GIIR Conference 2024! Thank you for creating your account.

Your account has been successfully created with the following details:
Email: {email}

You can now:
- Register for the conference
- Submit papers
- Access conference materials
- Stay updated with conference announcements

To get started, visit our website and log in with your email address.

If you have any questions, please don't hesitate to contact us.

Best regards,
GIIR Conference Team
"""

PASSWORD_RESET_EMAIL = """
Dear {full_name},

You recently requested to reset your password for your GIIR Conference account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour for security reasons.

If you did not request a password reset, please ignore this email or contact us if you have concerns.

Best regards,
GIIR Conference Team
""" 