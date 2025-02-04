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
    'hero_text_color': '#ffffff'
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

# Register filters with Flask app
def register_filters(app):
    app.jinja_env.filters['filesizeformat'] = format_filesize
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['filename'] = get_filename
    app.jinja_env.filters['status_badge'] = status_badge 