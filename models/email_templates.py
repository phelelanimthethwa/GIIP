REGISTRATION_CONFIRMATION = """
Dear {full_name},

Thank you for registering for Global Conferences!

Registration Details:
- Registration Type: {registration_type}
- Total Amount: {currency_symbol}{total_amount}
- Workshop: {workshop}
- Banquet: {banquet}

Please keep this email for your records.

Thanks & regards,
Global Conferences
"""

ABSTRACT_SUBMISSION_CONFIRMATION = """
Dear {author_name},

Thank you for submitting your abstract to {conference_name}.

Submission Details:
- Conference: {conference_name}
- Abstract Title: {paper_title}
- Presentation Type: {presentation_type}
- Submission ID: {paper_id}

We will review your submission and get back to you soon.

Thanks & regards,
Global Conferences
"""

# Backwards compatibility alias
PAPER_SUBMISSION_CONFIRMATION = ABSTRACT_SUBMISSION_CONFIRMATION

# HTML acceptance letter for abstract (multipart email alongside plain-text ABSTRACT_STATUS_UPDATE['accepted'])
ABSTRACT_ACCEPTANCE_EMAIL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Abstract accepted</title>
</head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background-color:#f1f5f9;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f1f5f9;">
        <tr>
            <td align="center" style="padding:32px 16px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:16px;box-shadow:0 4px 24px rgba(15,23,42,0.08);overflow:hidden;">
                    <tr>
                        <td style="padding:28px 40px 16px;text-align:center;border-bottom:1px solid #e2e8f0;">
                            <img src="{logo_url}" alt="Conference" style="max-width:220px;height:auto;display:inline-block;" />
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:24px 40px 8px;background:linear-gradient(135deg,#4338ca 0%,#7c3aed 100%);">
                            <p style="margin:0;color:rgba(255,255,255,0.92);font-size:13px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;">Letter of acceptance</p>
                            <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;line-height:1.35;">{conference_name}</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:32px 40px;color:#334155;font-size:16px;line-height:1.75;">
                            <p style="margin:0 0 16px;">Dear {author_name},</p>
                            <p style="margin:0 0 16px;"><strong>Congratulations!</strong> We are pleased to inform you that your abstract submission has been <strong>accepted</strong> for presentation at <strong>{conference_name}</strong>.</p>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:24px 0;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;">
                                <tr>
                                    <td style="padding:20px 24px;">
                                        <p style="margin:0 0 8px;color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:0.04em;">Abstract title</p>
                                        <p style="margin:0 0 16px;color:#0f172a;font-size:17px;font-weight:600;">{title}</p>
                                        <p style="margin:0 0 8px;color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:0.04em;">Presentation format</p>
                                        <p style="margin:0;color:#0f172a;">{type}</p>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0 0 12px;color:#475569;font-size:15px;"><strong>From the committee</strong></p>
                            <p style="margin:0;color:#475569;font-size:15px;white-space:pre-wrap;">{comments}</p>
                            <p style="margin:28px 0 0;color:#64748b;font-size:14px;">Your next step will be to submit the full paper once your registration is confirmed. Further instructions will be sent by email.</p>
                            <p style="margin:24px 0 0;color:#0f172a;">With kind regards,<br/><strong>Global Conferences</strong></p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color:#0f172a;padding:24px 40px;">
                            <p style="margin:0;color:#94a3b8;font-size:12px;line-height:1.6;">This message was sent regarding your abstract submission. If you have questions, reply to the conference secretariat.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

# Backwards compatibility alias
PAPER_ACCEPTANCE_EMAIL_HTML = ABSTRACT_ACCEPTANCE_EMAIL_HTML

ABSTRACT_STATUS_UPDATE = {
    'accepted': """
Congratulations! Your abstract has been accepted for presentation at Global Conferences.

Abstract Details:
Title: {title}
Presentation Type: {type}

Your next step is to complete the payment for your registration. Once payment is confirmed, you will be able to submit your full paper.
{comments}

Thanks & regards,
Global Conferences
""",
    'rejected': """
Thank you for submitting your abstract to Global Conferences.

We regret to inform you that your abstract was not accepted for presentation.

Abstract Details:
Title: {title}
Presentation Type: {type}

Review Comments:
{comments}

We encourage you to consider our feedback for future submissions.

Thanks & regards,
Global Conferences
""",
    'revision': """
Thank you for submitting your abstract to Global Conferences.

Your abstract requires revisions before it can be accepted.

Abstract Details:
Title: {title}
Presentation Type: {type}

Review Comments:
{comments}

Please submit your revised version through the conference system.

Thanks & regards,
Global Conferences
"""
}

# Backwards compatibility alias
PAPER_STATUS_UPDATE = ABSTRACT_STATUS_UPDATE

WELCOME_EMAIL = """
Dear {full_name},

Welcome to Global Conferences! Thank you for creating your account.

Your account has been successfully created with the following details:
Email: {email}

You can now:
- Register for conferences
- Submit papers
- Access conference materials
- Stay updated with conference announcements

To get started, visit our website and log in with your email address.

If you have any questions, please don't hesitate to contact us at admin@globalconferences.co.za.

Thanks & regards,
Global Conferences Admin
"""

PASSWORD_RESET_EMAIL = """
Dear {full_name},

You recently requested to reset your password for your Global Conferences account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour for security reasons.

If you did not request a password reset, please ignore this email or contact us if you have concerns.

Thanks & regards,
Global Conferences
"""

# Announcement Email Templates
ANNOUNCEMENT_EMAIL_TEXT = """
{title}

{content}

---
Scheduled for: {scheduled_date} at {scheduled_time} ({timezone})
Type: {announcement_type}

Thanks & regards,
Global Conferences

---
You received this email because you are registered with Global Conferences.
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
                                            <strong style="color: #ffffff;">Global Conferences</strong>
                                        </p>
                                        <p style="margin: 0 0 16px; color: #64748b;">
                                            You received this email because you are registered with Global Conferences.
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

# Admin notification when a paper is submitted
ADMIN_SUBMISSION_NOTIFICATION = """
New Paper Submission

A new paper has been submitted to {conference_name}.

Details:
- Paper Title: {paper_title}
- Submission ID: {paper_id}
- Author(s): {author_names}
- Submitter Email: {submitter_email}
- Presentation Type: {presentation_type}

Please log in to the admin dashboard to review this submission.

Thanks & regards,
Global Conferences
"""

# Full Paper submission confirmation
FULL_PAPER_SUBMISSION_CONFIRMATION = """
Dear {author_name},

Thank you for submitting your full paper to {conference_name}.

Submission Details:
- Conference: {conference_name}
- Abstract Title: {paper_title}
- Submission ID: {paper_id}
- Submitted: {submitted_at}

Your full paper has been received and is now part of your conference proceedings.

Thanks & regards,
Global Conferences
"""

# Admin notification when full paper is submitted
ADMIN_FULL_PAPER_SUBMISSION_NOTIFICATION = """
Full Paper Submitted

A full paper has been submitted for {conference_name}.

Details:
- Abstract Title: {paper_title}
- Submission ID: {paper_id}
- Author(s): {author_names}
- Submitter Email: {submitter_email}

Both the abstract and full paper are now available in the admin dashboard.

Thanks & regards,
Global Conferences
"""

REGISTRATION_REASSIGNMENT = """
Dear {full_name},

Your conference registration has been reassigned by our administration team (for example, if it was initially linked to the wrong conference).

Previous conference: {old_conference_name}
You are now registered for: {new_conference_name}
Conference code: {conference_code}

Your registration is pending review for this conference. You will be notified separately when it is approved or rejected, according to our usual process.

Open your registration for this conference:
{registration_portal_url}

If you have questions, contact us at {support_email}.

Thanks & regards,
Global Conferences
"""

# Type badge colors/text for announcements
ANNOUNCEMENT_TYPE_BADGES = {
    'important': '⚠️ Important',
    'info': '📋 Information',
    'event': '📅 Event',
    'update': '🔄 Update'
}


def _sample_context(public_base_url: str, logo_url: str) -> dict:
    """Sample values for admin email preview (must match template placeholders)."""
    base = (public_base_url or 'https://example.org').rstrip('/')
    logo = logo_url or f'{base}/static/images/placeholder-speaker1.jpg'
    return {
        'full_name': 'Dr. Jane Researcher',
        'email': 'jane.researcher@university.edu',
        'registration_type': 'Author (early bird)',
        'currency_symbol': 'R',
        'total_amount': '3,500.00',
        'workshop': 'Yes',
        'banquet': 'No',
        'author_name': 'Dr. Jane Researcher',
        'paper_title': 'Innovation Pathways in Global Research',
        'presentation_type': 'Oral Presentation',
        'paper_id': 'SUB-2026-0042',
        'conference_name': 'Global Conferences 2026',
        'title': 'Innovation Pathways in Global Research',
        'type': 'Oral Presentation',
        'comments': 'The committee congratulates you on a strong contribution. Please upload your camera-ready version by the stated deadline.',
        'reset_link': f'{base}/reset-password?token=sample-token',
        'logo_url': logo,
        'announcement_title': 'Keynote schedule published',
        'announcement_content': '<p>We have posted the <strong>keynote timetable</strong> on the conference site.</p>',
        'type_badge': ANNOUNCEMENT_TYPE_BADGES['info'],
        'scheduled_date': '15 September 2026',
        'scheduled_time': '09:00',
        'timezone': 'SAST',
        'image_section': '',
        'conference_url': base,
        'unsubscribe_url': f'{base}/profile#email-preferences',
        'announcement_type_plain': 'Info',
        'author_names': 'Dr. Jane Researcher, Prof. A. Coauthor',
        'submitter_email': 'jane.researcher@university.edu',
        'old_conference_name': 'Regional Conference 2025',
        'new_conference_name': 'Global Conferences 2026',
        'conference_code': 'GC2026-ABC',
        'registration_portal_url': f'{base}/conferences/sample-conf-id/register',
        'support_email': 'admin@globalconferences.co.za',
    }


def get_system_email_catalog(public_base_url: str, logo_url: str) -> list:
    """
    Metadata + rendered previews for emails defined in this module (source of truth).
    Used by the admin email templates page.
    """
    s = _sample_context(public_base_url, logo_url)
    items = []

    def add(oid, name, description, trigger, subject, body_fmt=None, html_fmt=None, extras=None):
        row = {
            'id': oid,
            'name': name,
            'description': description,
            'trigger': trigger,
            'subject': subject,
            'text_body': body_fmt.format(**s) if body_fmt else '',
            'html_body': html_fmt.format(**s) if html_fmt else '',
            'placeholders': sorted(set(extras or [])),
        }
        items.append(row)

    add(
        'welcome',
        'Welcome email',
        'Sent after a new user completes registration.',
        'User signup / `email_service.send_welcome_email()`',
        'Welcome to Global Conferences',
        body_fmt=WELCOME_EMAIL,
        extras=['full_name', 'email'],
    )
    add(
        'password_reset',
        'Password reset',
        'Sent when a user requests a password reset link.',
        'Forgot password flow / `send_password_reset_email()`',
        'Password Reset - Global Conferences',
        body_fmt=PASSWORD_RESET_EMAIL,
        extras=['full_name', 'reset_link'],
    )
    add(
        'registration_confirmation',
        'Registration confirmation',
        'Sent immediately after a paid or completed registration.',
        '`send_registration_confirmation()`',
        'Conference Registration Confirmation',
        body_fmt=REGISTRATION_CONFIRMATION,
        extras=['full_name', 'registration_type', 'currency_symbol', 'total_amount', 'workshop', 'banquet'],
    )
    add(
        'registration_reassignment',
        'Registration moved to another conference',
        'Sent when an admin reassigns a participant to the correct conference.',
        '`send_registration_reassignment_email()` / POST `/admin/registrations/.../reassign-conference`',
        f"Your registration has been moved to {s['new_conference_name']}",
        body_fmt=REGISTRATION_REASSIGNMENT,
        extras=[
            'full_name', 'email', 'old_conference_name', 'new_conference_name', 'conference_code',
            'registration_portal_url', 'support_email',
        ],
    )
    add(
        'paper_submission_confirmation',
        'Paper submission confirmation',
        'Sent to the submitting author after a paper is uploaded.',
        '`send_paper_confirmation()`',
        f"Paper Submission Confirmation - {s['conference_name']}",
        body_fmt=PAPER_SUBMISSION_CONFIRMATION,
        extras=['author_name', 'paper_title', 'presentation_type', 'paper_id', 'conference_name'],
    )
    add(
        'paper_accepted',
        'Paper accepted (emails + PDF letter)',
        'When a conference is linked, `send_acceptance_letter_email()` sends the full letter (HTML + this PDF attachment). If that fails, `send_paper_status_update(..., \'accepted\')` sends plain text + shorter HTML only.',
        'Admin sets paper to Accepted (with conference context) / `generate_acceptance_letter_pdf()`',
        'Paper Submission Accepted',
        body_fmt=PAPER_STATUS_UPDATE['accepted'],
        html_fmt=PAPER_ACCEPTANCE_EMAIL_HTML,
        extras=['title', 'type', 'comments', 'author_name', 'conference_name', 'logo_url'],
    )
    add(
        'paper_rejected',
        'Paper rejection letter',
        'Sent when a submission is not accepted.',
        'Status: Rejected',
        'Paper Submission Rejected',
        body_fmt=PAPER_STATUS_UPDATE['rejected'],
        extras=['title', 'type', 'comments'],
    )
    add(
        'paper_revision',
        'Revision requested',
        'Sent when reviewers request changes before acceptance.',
        'Status: Revision',
        'Paper Submission Revision',
        body_fmt=PAPER_STATUS_UPDATE['revision'],
        extras=['title', 'type', 'comments'],
    )
    add(
        'admin_submission_notify',
        'Admin: new paper submitted',
        'Internal notice to configured admin recipients.',
        '`send_submission_notification_to_admins()`',
        f"New Paper Submission - {s['paper_title']} [{s['conference_name']}]",
        body_fmt=ADMIN_SUBMISSION_NOTIFICATION,
        extras=[
            'conference_name', 'paper_title', 'paper_id', 'author_names',
            'submitter_email', 'presentation_type',
        ],
    )

    ann_html = ANNOUNCEMENT_EMAIL_HTML.format(
        title=s['announcement_title'],
        content=s['announcement_content'],
        type_badge=s['type_badge'],
        scheduled_date=s['scheduled_date'],
        scheduled_time=s['scheduled_time'],
        timezone=s['timezone'],
        image_section=s['image_section'],
        conference_url=s['conference_url'],
        unsubscribe_url=s['unsubscribe_url'],
    )
    ann_text = ANNOUNCEMENT_EMAIL_TEXT.format(
        title=s['announcement_title'],
        content='We have posted the keynote timetable on the conference site.',
        scheduled_date=s['scheduled_date'],
        scheduled_time=s['scheduled_time'],
        timezone=s['timezone'],
        announcement_type=s['announcement_type_plain'],
    )
    items.append({
        'id': 'announcement',
        'name': 'Broadcast announcement',
        'description': 'Bulk email to users who opted in to announcements.',
        'trigger': 'Admin announcement tool / `send_announcement_email()`',
        'subject': f"[Global Conferences] {s['announcement_title']}",
        'text_body': ann_text,
        'html_body': ann_html,
        'placeholders': ['title', 'content', 'type_badge', 'scheduled_date', 'scheduled_time', 'timezone', 'image_section', 'conference_url', 'unsubscribe_url'],
    })

    return items

