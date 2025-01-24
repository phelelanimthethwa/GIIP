from firebase_admin import db

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