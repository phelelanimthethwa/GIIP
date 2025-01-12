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
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'your-email@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'your-email-password'
    MAIL_DEFAULT_SENDER = MAIL_USERNAME 

    # reCAPTCHA configuration
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY') or 'your-recaptcha-site-key'
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY') or 'your-recaptcha-secret-key' 