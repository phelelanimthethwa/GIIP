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

Thank you for submitting your paper to {conference_name}.

Submission Details:
- Conference: {conference_name}
- Paper Title: {paper_title}
- Presentation Type: {presentation_type}
- Submission ID: {paper_id}

We will review your submission and get back to you soon.

Best regards,
{conference_name} Conference Team
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

# Announcement Email Templates
ANNOUNCEMENT_EMAIL_TEXT = """
{title}

{content}

---
Scheduled for: {scheduled_date} at {scheduled_time} ({timezone})
Type: {announcement_type}

Best regards,
GIIR Conference Team

---
You received this email because you are registered with GIIR Conference.
To manage your email preferences, visit your account settings.
"""

ANNOUNCEMENT_EMAIL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08); overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 40px 32px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; padding: 6px 14px; background-color: rgba(255,255,255,0.2); border-radius: 20px; color: #ffffff; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;">{type_badge}</span>
                                        <h1 style="margin: 16px 0 0; color: #ffffff; font-size: 28px; font-weight: 700; line-height: 1.3;">{title}</h1>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Date & Time Bar -->
                    <tr>
                        <td style="background-color: #f1f5f9; padding: 16px 40px; border-bottom: 1px solid #e2e8f0;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="color: #64748b; font-size: 14px;">
                                        <span style="display: inline-block; margin-right: 24px;">
                                            📅 <strong style="color: #334155;">{scheduled_date}</strong>
                                        </span>
                                        <span style="display: inline-block; margin-right: 24px;">
                                            🕐 <strong style="color: #334155;">{scheduled_time}</strong>
                                        </span>
                                        <span style="display: inline-block;">
                                            🌍 <strong style="color: #334155;">{timezone}</strong>
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            {image_section}
                            <div style="color: #374151; font-size: 16px; line-height: 1.7;">
                                {content}
                            </div>
                        </td>
                    </tr>
                    
                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 40px 40px;">
                            <table role="presentation" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="border-radius: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                                        <a href="{conference_url}" target="_blank" style="display: inline-block; padding: 14px 32px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600;">
                                            View Conference Details →
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #1e293b; padding: 32px 40px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td style="color: #94a3b8; font-size: 13px; line-height: 1.6;">
                                        <p style="margin: 0 0 12px;">
                                            <strong style="color: #ffffff;">GIIR Conference</strong>
                                        </p>
                                        <p style="margin: 0 0 16px; color: #64748b;">
                                            You received this email because you are registered with GIIR Conference.
                                        </p>
                                        <p style="margin: 0;">
                                            <a href="{unsubscribe_url}" style="color: #667eea; text-decoration: none;">Manage Email Preferences</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

# Type badge colors/text for announcements
ANNOUNCEMENT_TYPE_BADGES = {
    'important': '⚠️ Important',
    'info': '📋 Information',
    'event': '📅 Event',
    'update': '🔄 Update'
} 