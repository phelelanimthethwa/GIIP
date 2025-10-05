from firebase_admin import db
import os
from datetime import datetime

# Default theme settings
DEFAULT_THEME = {
    'primary_color': '#007bff',
    'secondary_color': '#6c757d',
    'accent_color': '#28a745',
    'text_color': '#333333',
    'background_color': '#ffffff',
    'header_background': '#f8f9fa',
    'footer_background': '#343a40',
    'hero_text_color': '#ffffff',
    'subtitle_marquee': True  # Default to enabled
}

def get_site_design():
    """
    Get the site design settings from Firebase.
    Returns the design settings or default theme if none exists.
    """
    try:
        design_ref = db.reference('site_design')
        design = design_ref.get()
        return design if design else DEFAULT_THEME
    except Exception as e:
        print(f"Error fetching site design: {str(e)}")
        return DEFAULT_THEME

def format_filesize(size):
    """Format file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def format_datetime(dt_str):
    """Format datetime string to human readable format"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except:
        return dt_str

def format_date(dt_str):
    """Format datetime string to date only (no time)"""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%B %d, %Y")
    except:
        return dt_str

def get_filename(filepath):
    """Get original filename from path"""
    return os.path.basename(filepath)

def status_badge(status):
    """Convert status to badge color class"""
    status_colors = {
        'pending': 'warning',
        'accepted': 'success',
        'rejected': 'danger',
        'revision': 'info'
    }
    return status_colors.get(status.lower(), 'secondary')

def generate_conference_code(conference_abbr, year):
    """
    Generate a unique conference code in the format: CONF-[YEAR]-[ABBREVIATION]-[UNIQUE_ID]

    Args:
        conference_abbr: Conference abbreviation (e.g., 'ETL', 'STM', 'TBME', 'SAT')
        year: Conference year (e.g., 2026, 2027)

    Returns:
        str: Unique conference code (e.g., 'CONF-2026-ETL-A1B2C3D4')
    """
    import random
    import string

    # Generate 8-character alphanumeric unique ID
    unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    return f"CONF-{year}-{conference_abbr}-{unique_id}"

def validate_conference_code(code):
    """
    Validate conference code format and check if it exists in database

    Args:
        code: Conference code to validate

    Returns:
        dict: {'valid': bool, 'conference_id': str, 'error': str}
    """
    import re
    from firebase_admin import db

    try:
        # Expected format: CONF-YYYY-XXX-XXXXXXXX (where X are alphanumeric)
        pattern = r'^CONF-(\d{4})-([A-Z]{3,4})-([A-Z0-9]{8})$'

        match = re.match(pattern, code.upper())
        if not match:
            return {'valid': False, 'error': 'Invalid conference code format'}

        year, abbr, unique_id = match.groups()

        # Search for conference with this code in Firebase
        conferences_ref = db.reference('conferences')
        conferences = conferences_ref.get() or {}

        for conference_id, conference_data in conferences.items():
            if conference_data.get('conference_code') == code.upper():
                return {
                    'valid': True,
                    'conference_id': conference_id,
                    'conference': conference_data
                }

        return {'valid': False, 'error': 'Conference code not found'}

    except Exception as e:
        return {'valid': False, 'error': str(e)}

def get_conference_by_code(code):
    """
    Get conference data by unique conference code

    Args:
        code: Conference code

    Returns:
        dict: Conference data or None
    """
    from firebase_admin import db

    try:
        conferences_ref = db.reference('conferences')
        conferences = conferences_ref.get() or {}

        for conference_id, conference_data in conferences.items():
            if conference_data.get('conference_code') == code.upper():
                return {
                    'conference_id': conference_id,
                    'conference_data': conference_data
                }

        return None
    except Exception as e:
        print(f"Error getting conference by code: {e}")
        return None

# Register filters with Flask app
def register_filters(app):
    app.jinja_env.filters['filesizeformat'] = format_filesize
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['date'] = format_date
    app.jinja_env.filters['filename'] = get_filename
    app.jinja_env.filters['status_badge'] = status_badge 