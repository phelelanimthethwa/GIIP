import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Firebase Configuration
    FIREBASE_CONFIG = {
        'apiKey': 'AIzaSyBsMIXeEKHGMQGWwEHg_nT1QdlOT_zCxYY',
        'authDomain': 'giir-66ae6.firebaseapp.com',
        'databaseURL': 'https://giir-66ae6-default-rtdb.firebaseio.com',
        'projectId': 'giir-66ae6',
        'storageBucket': 'giir-66ae6.appspot.com',
        'messagingSenderId': '107515441970013958036',
        'appId': '1:107515441970013958036:web:your-app-id'
    }
    
    # Email Configuration
    MAIL_SERVER = 'smtp.office365.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'tg@deployeverywhere.com'
    MAIL_PASSWORD = 'KXRUIKIrJ$hHbx#q12@EM1'
    MAIL_DEFAULT_SENDER = 'GIIR Conference <tg@deployeverywhere.com>'
    MAIL_MAX_EMAILS = None
    MAIL_ASCII_ATTACHMENTS = False
    MAIL_SUPPRESS_SEND = False
    MAIL_DEBUG = True

    # reCAPTCHA configuration
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY') or 'your-recaptcha-site-key'
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY') or 'your-recaptcha-secret-key' 