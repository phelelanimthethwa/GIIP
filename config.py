import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()  # Load environment variables from .env file

class Config:
    # SECRET_KEY: Use environment variable, raise error in production if not set
    _secret_key = os.environ.get('SECRET_KEY')
    if os.environ.get('FLASK_ENV') == 'production':
        if not _secret_key:
            raise ValueError("SECRET_KEY must be set in production environment")
        SECRET_KEY = _secret_key
    else:
        SECRET_KEY = _secret_key or 'dev-secret-key-replace-in-production'
    
    # Google Gemini Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Firebase Configuration
    FIREBASE_CONFIG = {
        'apiKey': os.environ.get('FIREBASE_API_KEY'),
        'authDomain': os.environ.get('FIREBASE_AUTH_DOMAIN'),
        'databaseURL': os.environ.get('FIREBASE_DATABASE_URL'),
        'projectId': os.environ.get('FIREBASE_PROJECT_ID'),
        'storageBucket': 'giir-66ae6.appspot.com',  # Corrected storage bucket format
        'messagingSenderId': os.environ.get('FIREBASE_MESSAGING_SENDER_ID'),
        'appId': os.environ.get('FIREBASE_APP_ID')
    }
    
    # Email Configuration (Resend)
    # Supports both 'RESEND_API_KEY' and legacy 'Resend_api_key' environment variable names
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY') or os.environ.get('Resend_api_key')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@globalconference.co.za'

    # Admin Configuration
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@giirconference.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')  # Must be set via environment variable

    # reCAPTCHA configuration
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')

    # Google Maps configuration
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
    
    # Yoco Payment Gateway Configuration
    YOCO_SECRET_KEY = os.environ.get('YOCO_SECRET_KEY')
    YOCO_PUBLIC_KEY = os.environ.get('YOCO_PUBLIC_KEY')
    YOCO_BASE_URL = os.environ.get('YOCO_BASE_URL', 'https://payments.yoco.com')
    YOCO_WEBHOOK_SECRET = os.environ.get('YOCO_WEBHOOK_SECRET')
    YOCO_RETURN_URL = os.environ.get('YOCO_RETURN_URL', 'https://globalconference.co.za/payment/callback')
    YOCO_CANCEL_URL = os.environ.get('YOCO_CANCEL_URL', 'https://globalconference.co.za/payment/cancelled')

    # TinyMCE configuration
    TINYMCE_API_KEY = os.environ.get('TINYMCE_API_KEY')

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)