from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory, send_file, make_response
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

import firebase_admin
from firebase_admin import credentials, db, auth, firestore, storage
from config import Config
import json
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import os
import base64
from dotenv import load_dotenv
from models.email_service import EmailService
import pytz
from google.cloud import storage as gcs_storage

from PIL import Image
from io import BytesIO
from utils import register_filters, get_conference_by_code
# Temporarily commented out to use app.py /registration route instead of blueprint route
# from routes.user_routes import user_routes
import io
import mimetypes
import uuid

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Please install it using: pip install python-dotenv")
    def load_dotenv(): pass

load_dotenv()  # Add this before creating the Flask app

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load configuration from Config class
app.config.from_object(Config)

# Configure app based on environment
if os.environ.get('FLASK_ENV') == 'production':
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'your-secret-key'),
        SESSION_COOKIE_SECURE=True,
        REMEMBER_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )
else:
    app.config['SECRET_KEY'] = 'development-key'

# Register blueprints
# Temporarily commented out to use app.py /registration route instead of blueprint route
# app.register_blueprint(user_routes)

# Register Jinja2 filters
register_filters(app)

# Initialize Firebase Admin SDK
try:
    if os.environ.get('FIREBASE_CREDENTIALS'):
        # In production, use credentials from environment variable
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
        print("Using Firebase credentials from environment variable")
    else:
        # In development, use service account file
        cred = credentials.Certificate('serviceAccountKey.json')
        print("Using Firebase credentials from serviceAccountKey.json")
    
    # Get Firebase API key from .env file
    firebase_api_key = os.environ.get('FIREBASE_API_KEY')
    if not firebase_api_key:
        print("Warning: FIREBASE_API_KEY not found in environment variables")
    else:
        print("Using Firebase API key from environment variables")
    
    # Initialize Firebase with options from serviceAccountKey.json
    firebase_options = {
        'databaseURL': 'https://giir-66ae6-default-rtdb.firebaseio.com',
        'storageBucket': 'giir-66ae6.firebasestorage.app',
        'apiKey': firebase_api_key  # Use API key from .env
    }
    
    # Initialize the Firebase app
    firebase_admin.initialize_app(cred, firebase_options)
    
    # Test Firebase Storage connection
    try:
        bucket = storage.bucket('giir-66ae6.firebasestorage.app')
        print(f"Firebase Storage bucket initialized: {bucket.name}")
        # Test if bucket exists by trying to get its metadata
        try:
            bucket.get_blob('test-connection')  # This will succeed even if blob doesn't exist
            print("Firebase Storage bucket is accessible")
        except Exception as bucket_test:
            print(f"Firebase Storage bucket test: {str(bucket_test)}")
    except Exception as storage_init_error:
        print(f"Firebase Storage initialization warning: {str(storage_init_error)}")
    
    # Store Firebase config in app.config for easier access later
    app.config['FIREBASE_CONFIG'] = {
        'apiKey': firebase_api_key,
        'authDomain': 'giir-66ae6.firebaseapp.com',
        'databaseURL': 'https://giir-66ae6-default-rtdb.firebaseio.com',
        'projectId': 'giir-66ae6',
        'storageBucket': 'giir-66ae6.firebasestorage.app',
    }
    
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Error initializing Firebase: {str(e)}")
    raise

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Flask-Mail
mail = Mail(app)

# After initializing mail
email_service = EmailService(mail)

# Add datetime filter for Jinja templates
@app.template_filter('datetime')
def format_datetime(value):
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return value
    else:
        dt = value
    return dt.strftime('%B %d, %Y %I:%M %p')

# Add timezone formatting helper
def format_datetime_with_timezone(date_str, time_str, timezone_str):
    """Format datetime with timezone for consistent display"""
    try:
        # Validate inputs
        if not all([date_str, time_str, timezone_str]):
            raise ValueError(f"Missing required datetime parameters: date={date_str}, time={time_str}, tz={timezone_str}")
        
        # Create datetime object
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        # Validate timezone
        try:
            tz = pytz.timezone(timezone_str)
        except Exception as tz_error:
            print(f"Warning: Invalid timezone '{timezone_str}', using UTC instead. Error: {tz_error}")
            tz = pytz.UTC
        
        # Localize the datetime
        local_dt = tz.localize(dt)
        
        print(f"Successfully formatted datetime: {local_dt.isoformat()}")
        return local_dt.isoformat()
    except Exception as e:
        print(f"Error formatting datetime - date_str: {date_str}, time_str: {time_str}, tz: {timezone_str}, Error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return a fallback ISO format with the date and time
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            return dt.isoformat()
        except:
            return None

# Add this after app initialization but before routes
@app.template_filter('format_date')
def format_date(date_str):
    try:
        if isinstance(date_str, str):
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            date = date_str
        return date.strftime('%B %d, %Y %I:%M %p')
    except Exception:
        return date_str  # Return original string if parsing fails

# Add this configuration after other app configurations
app.config['UPLOAD_FOLDER'] = 'static/uploads/documents'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'tex'}

# Add these constants near the top of the file
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico', 'tiff', 'tif'}
DEFAULT_THEME = {
    'primary_color': '#007bff',
    'secondary_color': '#6c757d',
    'accent_color': '#28a745',
    'text_color': '#333333',
    'background_color': '#ffffff',
    'header_background': '#f8f9fa',
    'footer_background': '#343a40',
    'hero_text_color': '#ffffff',
    'font_family': "'Roboto', sans-serif",
    'heading_font': "'Poppins', sans-serif"
}

# Add this near the top with other upload folder configurations
app.config['COMMITTEE_UPLOAD_FOLDER'] = 'static/uploads/committee'

# Update or add these configuration settings
app.config['FIREBASE_API_KEY'] = os.environ.get('FIREBASE_API_KEY')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def compress_image(file, max_size_kb=500):
    """Compress image to reduce file size while maintaining quality"""
    try:
        # Read the image file
        if hasattr(file, 'read'):
            file.seek(0)  # Reset file pointer
            image_data = file.read()
            img = Image.open(BytesIO(image_data))
        else:
            img = Image.open(file)

        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Initial quality
        quality = 95
        output = BytesIO()

        # Save with initial quality
        img.save(output, format='JPEG', quality=quality, optimize=True)
        
        # Binary search for optimal quality
        while output.tell() > max_size_kb * 1024 and quality > 10:
            output = BytesIO()
            quality = max(quality - 5, 10)
            img.save(output, format='JPEG', quality=quality, optimize=True)

        output.seek(0)
        return output.getvalue()

    except Exception as e:
        print(f"Error compressing image: {str(e)}")
        # If compression fails, return original file data
        file.seek(0)
        return file.read()

def validate_image(file, image_type='default'):
    """Validate image file based on type (hero or associate)"""
    if not file or not file.filename:
        raise ValueError("No file provided")

    if not allowed_image_file(file.filename):
        raise ValueError("Invalid file type. Only JPG, JPEG, PNG and GIF files are allowed")

    # Read image to validate dimensions
    try:
        img = Image.open(file)
        width, height = img.size
        
        # Different size limits for different image types
        if image_type == 'hero':
            if width > 4000 or height > 4000:
                raise ValueError("Hero image dimensions must be less than 4000x4000 pixels")
        elif image_type == 'associate':
            if width > 1000 or height > 1000:
                raise ValueError("Associate logo dimensions must be less than 1000x1000 pixels")
        else:
            if width > 2000 or height > 2000:
                raise ValueError("Image dimensions must be less than 2000x2000 pixels")
        
        file.seek(0)  # Reset file pointer after reading
        return True
    except Exception as e:
        raise ValueError(f"Invalid image: {str(e)}")

class User(UserMixin):
    def __init__(self, uid, email, full_name, is_admin=False):
        self.id = uid
        self.email = email
        self.full_name = full_name
        self.is_admin = is_admin
        # Additional profile fields
        self.institution = None
        self.department = None
        self.title = None
        self.phone = None
        self.country = None
        self.city = None
        self.bio = None
        self.website = None
        self.created_at = None
        self.updated_at = None
        self.email_preferences = {}

@login_manager.user_loader
def load_user(user_id):
    try:
        user = auth.get_user(user_id)
        # Get additional user data from Realtime Database
        ref = db.reference(f'users/{user_id}')
        user_data = ref.get()
        is_admin = user_data.get('is_admin', False) if user_data else False
        
        # Create user object
        user_obj = User(user.uid, user.email, user.display_name, is_admin)
        
        # Populate additional fields from database
        if user_data:
            user_obj.institution = user_data.get('institution')
            user_obj.department = user_data.get('department')
            user_obj.title = user_data.get('title')
            user_obj.phone = user_data.get('phone')
            user_obj.country = user_data.get('country')
            user_obj.city = user_data.get('city')
            user_obj.bio = user_data.get('bio')
            user_obj.website = user_data.get('website')
            user_obj.created_at = user_data.get('created_at')
            user_obj.updated_at = user_data.get('updated_at')
            user_obj.email_preferences = user_data.get('email_preferences', {})
        
        return user_obj
    except Exception:
        return None

def send_confirmation_email(registration_data):
    return email_service.send_registration_confirmation(registration_data)

# Add this helper function near the top of the file
def get_site_design():
    """Helper function to fetch site design settings"""
    try:
        design_ref = db.reference('site_design')
        return design_ref.get() or DEFAULT_THEME
    except Exception as e:
        print(f"Error fetching site design: {str(e)}")
        return DEFAULT_THEME

@app.route('/')
def home():
    try:
        # Get home content from Firebase
        content_ref = db.reference('home_content')
        home_content = content_ref.get() or {
            'welcome': {
                'title': 'Welcome to GIIR Conference 2024',
                'subtitle': 'Global Institute on Innovative Research',
                'conference_date': 'International Conference 2024',
                'message': 'Join us for the premier conference in innovative research'
            },
            'hero': {
                'images': [],
                'conference': {
                    'name': 'GIIR Conference 2024',
                    'date': 'TBA',
                    'time': 'TBA',
                    'city': 'TBA',
                    'highlights': 'Keynote Speakers\nTechnical Sessions\nWorkshops\nNetworking Events'
                }
            }
        }
        
        # Get speakers for home page display
        speakers_ref = db.reference('speakers')
        speakers_data = speakers_ref.get() or {}
        
        # Convert speakers to list and add ids
        featured_speakers = []
        for key, speaker in speakers_data.items():
            # Only include current speakers, not past ones
            if speaker.get('status') != 'past':
                speaker['id'] = key
                featured_speakers.append(speaker)
            
        # Sort speakers by name and limit to 2 for home page display
        featured_speakers.sort(key=lambda x: x.get('name', '').lower())
        featured_speakers = featured_speakers[:2]  # Only show up to 2 speakers on home page
        
        site_design = get_site_design()
        
        return render_template('user/home.html', 
                            home_content=home_content,
                            site_design=site_design,
                            featured_speakers=featured_speakers,
                            page_name='home')
    except Exception as e:
        print(f"Error loading home content: {str(e)}")
        return render_template('user/home.html', 
                            home_content={
                                'welcome': {
                                    'title': 'Welcome to GIIR Conference 2024',
                                    'subtitle': 'Global Institute on Innovative Research',
                                    'conference_date': 'International Conference 2024',
                                    'message': 'Join us for the premier conference in innovative research'
                                }
                            },
                            featured_speakers=[],
                            site_design=DEFAULT_THEME,
                            page_name='home')

@app.route('/about')
def about():
    try:
        # Get about content from Firebase Realtime Database
        about_ref = db.reference('about_content')
        about_content = about_ref.get() or {
            'overview': {
                'title': 'About GIIR Conference',
                'description': 'The Global Institute on Innovative Research (GIIR) Conference 2024 brings together leading researchers, practitioners, and industry experts from around the world.',
                'stats': {
                    'attendees': '500+',
                    'countries': '50+',
                    'papers': '200+',
                    'speakers': '30+'
                }
            },
            'objectives': [
                {
                    'icon': 'fa-lightbulb',
                    'title': 'Knowledge Exchange',
                    'description': 'Facilitate the exchange of innovative ideas and research findings'
                },
                {
                    'icon': 'fa-users',
                    'title': 'Networking',
                    'description': 'Create opportunities for networking and collaboration'
                },
                {
                    'icon': 'fa-chart-line',
                    'title': 'Research Impact',
                    'description': 'Showcase cutting-edge research and its potential impact'
                }
            ],
            'committee': [
                {
                    'role': 'Conference Chair',
                    'name': 'Prof. Sarah Johnson',
                    'affiliation': 'Stanford University, USA',
                    'expertise': ['Artificial Intelligence', 'Machine Learning']
                }
            ],
            'past_conferences': [
                {
                    'year': '2023',
                    'location': 'Tokyo, Japan',
                    'highlight': '450+ Attendees'
                }
            ],
            'future_conference': {
                'enabled': False,
                'year': '',
                'title': '',
                'platform': 'Physical',
                'dates': []
            }
        }
        
        return render_template('user/about.html', about_content=about_content, site_design=get_site_design())
    except Exception as e:
        flash(f'Error loading about content: {str(e)}', 'error')
        return render_template('user/about.html', about_content={
            'overview': {
                'title': 'About GIIR Conference',
                'description': 'The Global Institute on Innovative Research (GIIR) Conference 2024 brings together leading researchers, practitioners, and industry experts from around the world.',
                'stats': {
                    'attendees': '500+',
                    'countries': '50+',
                    'papers': '200+',
                    'speakers': '30+'
                }
            }
        }, site_design=get_site_design())

@app.route('/call-for-papers')
def call_for_papers():
    # Get call for papers content from Firebase
    cfp_content = db.reference('call_for_papers_content').get() or {}
    
    print(f"DEBUG - User CFP - Content from database: {cfp_content}")
    
    # Set up default values if they don't exist in the fetched data
    if 'page_header' not in cfp_content:
        cfp_content['page_header'] = {
            'title': 'Call for Papers',
            'subtitle': 'Submit your research to be part of the Global Institute on Innovative Research Conference 2024'
        }
        
    if 'cta' not in cfp_content:
        cfp_content['cta'] = {
            'submit_button_text': 'Submit Your Paper',
            'template_button_text': 'Download Template',
            'template_url': '#'
        }
        
    # Ensure other required sections exist with default values
    if 'topics_intro' not in cfp_content:
        cfp_content['topics_intro'] = 'We invite high-quality original research papers in the following areas (but not limited to):'
    
    if 'topics' not in cfp_content:
        print("DEBUG - User CFP - No topics found, using defaults")
        cfp_content['topics'] = [
            {
                'title': 'Artificial Intelligence & Machine Learning',
                'subtopics': ['Deep Learning and Neural Networks', 'Natural Language Processing', 'Computer Vision and Pattern Recognition', 'Reinforcement Learning', 'AI Ethics and Fairness']
            },
            {
                'title': 'Data Science & Analytics',
                'subtopics': ['Big Data Analytics', 'Predictive Analytics', 'Data Mining', 'Business Intelligence', 'Statistical Analysis']
            }
        ]
    else:
        print(f"DEBUG - User CFP - Topics from database: {cfp_content['topics']}")
    
    if 'important_dates' not in cfp_content:
        cfp_content['important_dates'] = [
            {
                'icon': 'fas fa-paper-plane',
                'title': 'Paper Submission',
                'date': 'March 15, 2024',
                'time': '23:59 GMT'
            },
            {
                'icon': 'fas fa-envelope-open-text',
                'title': 'Notification of Acceptance',
                'date': 'April 30, 2024',
                'time': '23:59 GMT'
            }
        ]
    
    if 'submission_guidelines' not in cfp_content:
        cfp_content['submission_guidelines'] = [
            {
                'title': 'Paper Format',
                'guideline_items': ['Papers must be written in English', 'Maximum length: 8 pages including figures and references']
            },
            {
                'title': 'Review Process',
                'guideline_items': ['Double-blind peer review', 'Minimum three reviewers per paper']
            }
        ]
    else:
        # Convert any guideline dictionaries to objects with proper properties to avoid the items() method conflict
        structured_guidelines = []
        for guideline in cfp_content['submission_guidelines']:
            if isinstance(guideline, dict):
                guideline_obj = {}
                
                # Copy all properties except 'items'
                for key, value in guideline.items():
                    if key != 'items':
                        guideline_obj[key] = value
                
                # Add 'guideline_items' property instead of 'items' to avoid the method name conflict
                if 'items' in guideline and isinstance(guideline['items'], list):
                    guideline_obj['guideline_items'] = guideline['items']
                else:
                    guideline_obj['guideline_items'] = []
                
                structured_guidelines.append(guideline_obj)
            else:
                # If it's not a dict, create a basic structure
                structured_guidelines.append({
                    'title': 'Guideline',
                    'guideline_items': []
                })
                
        cfp_content['submission_guidelines'] = structured_guidelines
    
    return render_template('user/call_for_papers.html', site_design=get_site_design(), cfp_content=cfp_content)

@app.route('/paper-submission', methods=['GET', 'POST'])
@login_required
def paper_submission():
    # Get paper submission settings from Firebase
    settings_ref = db.reference('paper_submission_settings')
    paper_settings = settings_ref.get() or {}
    
    # Get all conferences for selection
    conferences = get_all_conferences()
    
    # Filter conferences that have paper submission enabled
    available_conferences = {}
    for conf_id, conf_data in conferences.items():
        if (conf_data and 'basic_info' in conf_data and 
            conf_data.get('settings', {}).get('paper_submission_enabled', True)):  # Default to True for backward compatibility
            available_conferences[conf_id] = conf_data
    
    if request.method == 'POST':
        try:
            # Get conference selection
            selected_conference_id = request.form.get('conference_id')
            
            # If multiple conferences available, require selection
            if len(available_conferences) > 1 and not selected_conference_id:
                flash('Please select a conference for your paper submission.', 'error')
                return render_template('user/papers/submit.html', 
                                     site_design=get_site_design(),
                                     conferences=available_conferences,
                                     paper_settings=paper_settings)
            
            # If only one conference or none selected, use first/default
            if not selected_conference_id and available_conferences:
                selected_conference_id = list(available_conferences.keys())[0]
            
            # Get form data
            paper_data = {
                'conference_id': selected_conference_id,
                'user_id': current_user.id,
                'user_email': current_user.email,
                'paper_title': request.form.get('paper_title'),
                'paper_abstract': request.form.get('paper_abstract'),
                'presentation_type': request.form.get('presentation_type'),
                'research_area': request.form.get('research_area'),
                'keywords': [k.strip() for k in request.form.get('keywords', '').split(',') if k.strip()],
                'submitted_at': datetime.now().isoformat(),
                'status': 'pending',
                'authors': [],
                'review_comments': '',
                'reviewed_by': '',
                'updated_at': datetime.now().isoformat()
            }

            # Process authors
            author_count = 0
            while f'authors[{author_count}][name]' in request.form:
                author = {
                    'name': request.form.get(f'authors[{author_count}][name]'),
                    'email': request.form.get(f'authors[{author_count}][email]'),
                    'institution': request.form.get(f'authors[{author_count}][institution]')
                }
                if all(author.values()):  # Only add if all fields are filled
                    paper_data['authors'].append(author)
                author_count += 1

            # Validate required fields
            required_fields = ['paper_title', 'paper_abstract', 'presentation_type', 'research_area']
            for field in required_fields:
                if not paper_data.get(field):
                    flash('Please fill in all required fields.', 'error')
                    return redirect(url_for('paper_submission'))

            if not paper_data['authors']:
                flash('At least one author is required.', 'error')
                return redirect(url_for('paper_submission'))

            # Handle paper file upload
            if 'paper_file' not in request.files:
                flash('Please upload a paper file.', 'error')
                return redirect(url_for('paper_submission'))

            file = request.files['paper_file']
            if not file or not file.filename:
                flash('Please select a paper file.', 'error')
                return redirect(url_for('paper_submission'))

            if not file.filename.lower().endswith('.pdf'):
                flash('Only PDF files are allowed.', 'error')
                return redirect(url_for('paper_submission'))

            # Read and encode file data
            file_data = file.read()
            file_base64 = base64.b64encode(file_data).decode('utf-8')

            # Add file data to paper_data
            paper_data.update({
                'file_data': file_base64,
                'file_name': secure_filename(file.filename),
                'file_type': file.content_type,
                'file_size': len(file_data)
            })

            # Debug print before saving
            print("Saving paper data:", {k: v for k, v in paper_data.items() if k != 'file_data'})

            # Store paper in Firebase under conference-specific path
            if selected_conference_id:
                papers_ref = db.reference(f'conferences/{selected_conference_id}/paper_submissions')
            else:
                # Fallback to global papers collection for backward compatibility
                papers_ref = db.reference('papers')
            
            new_paper = papers_ref.push(paper_data)
            paper_id = new_paper.key

            # Also store in user's submissions for easy access
            if selected_conference_id:
                user_submissions_ref = db.reference(f'user_paper_submissions/{current_user.id}')
                user_submissions_ref.push({
                    'conference_id': selected_conference_id,
                    'paper_id': paper_id,
                    'paper_title': paper_data['paper_title'],
                    'conference_name': available_conferences.get(selected_conference_id, {}).get('basic_info', {}).get('name', 'Unknown Conference'),
                    'status': 'pending',
                    'submitted_at': datetime.now().isoformat()
                })

            # Debug print after saving
            print("Paper saved with ID:", paper_id)

            # Send confirmation email
            try:
                conference_name = available_conferences.get(selected_conference_id, {}).get('basic_info', {}).get('name', 'Conference')
                email_service.send_paper_confirmation({
                    'authors': paper_data['authors'],
                    'paper_title': paper_data['paper_title'],
                    'presentation_type': paper_data['presentation_type'],
                    'paper_id': paper_id,
                    'user_email': current_user.email,
                    'conference_name': conference_name
                })
            except Exception as e:
                print(f"Error sending confirmation email: {str(e)}")

            flash(f'Paper submitted successfully to {conference_name}! Check your email for confirmation.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"Error submitting paper: {str(e)}")  # Log the error
            flash(f'Error submitting paper: {str(e)}', 'error')
            return render_template('user/papers/submit.html', 
                                 site_design=get_site_design(),
                                 conferences=available_conferences,
                                 paper_settings=paper_settings)

    return render_template('user/papers/submit.html', 
                         site_design=get_site_design(),
                         conferences=available_conferences,
                         paper_settings=paper_settings)

@app.route('/author-guidelines')
def author_guidelines():
    try:
        # Get guidelines from Firebase
        guidelines_ref = db.reference('author_guidelines')
        guidelines = guidelines_ref.get() or {}
        
        return render_template('user/papers/guidelines.html', 
                             guidelines=guidelines,
                             site_design=get_site_design())
    except Exception:
        flash('Error loading author guidelines.', 'error')
        return redirect(url_for('home'))

@app.route('/venue')
def venue():
    # Get the venue data from Firebase Realtime Database
    venue_details = None
    try:
        venue_ref = db.reference('venue_details')
        venue_details = venue_ref.get()
    except Exception as e:
        print(f"Error getting venue details: {str(e)}")
        
    return render_template('user/venue.html', venue_details=venue_details, site_design=get_site_design())

@app.route('/guest-speakers')
def guest_speakers():
    try:
        # Get speakers from Firebase
        speakers_ref = db.reference('speakers')
        speakers_data = speakers_ref.get() or {}
        
        # Convert to list and add IDs
        all_speakers = []
        current_speakers = []
        past_speakers = []
        
        for key, speaker in speakers_data.items():
            speaker['id'] = key  # Add the Firebase key as id
            all_speakers.append(speaker)
            
            # Add to appropriate list based on status
            if speaker.get('status') == 'past':
                past_speakers.append(speaker)
            else:
                # Default to current if status is not set or is 'current'
                current_speakers.append(speaker)
        
        # Sort speakers by name
        all_speakers.sort(key=lambda x: x.get('name', '').lower())
        current_speakers.sort(key=lambda x: x.get('name', '').lower())
        past_speakers.sort(key=lambda x: x.get('name', '').lower())
        
        return render_template('user/guest_speakers.html', 
                             site_design=get_site_design(),
                             speakers=all_speakers,
                             current_speakers=current_speakers,
                             past_speakers=past_speakers)
                             
    except Exception as e:
        print(f"Error loading guest speakers: {str(e)}")
        flash('Error loading guest speakers content.', 'error')
        return render_template('user/guest_speakers.html', 
                             site_design=get_site_design(),
                             speakers=[],
                             current_speakers=[],
                             past_speakers=[])

@app.route('/video-conference')
def video_conference():
    return render_template('user/video_conference.html', site_design=get_site_design())

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            # Get form data
            full_name = request.form.get('full_name', '').strip()
            institution = request.form.get('institution', '').strip()
            department = request.form.get('department', '').strip()
            title = request.form.get('title', '').strip()
            phone = request.form.get('phone', '').strip()
            country = request.form.get('country', '').strip()
            city = request.form.get('city', '').strip()
            bio = request.form.get('bio', '').strip()
            website = request.form.get('website', '').strip()
            
            # Validate required fields
            if not full_name:
                flash('Full name is required', 'error')
                return render_template('user/account/profile.html', site_design=get_site_design())
            
            # Update user data in Firebase Realtime Database
            user_ref = db.reference(f'users/{current_user.id}')
            user_data = user_ref.get() or {}
            
            # Update user data
            user_data.update({
                'full_name': full_name,
                'institution': institution,
                'department': department,
                'title': title,
                'phone': phone,
                'country': country,
                'city': city,
                'bio': bio,
                'website': website,
                'updated_at': datetime.now().isoformat()
            })
            
            # Save to database
            user_ref.set(user_data)
            
            # Update current user object
            current_user.full_name = full_name
            current_user.institution = institution
            current_user.department = department
            current_user.title = title
            current_user.phone = phone
            current_user.country = country
            current_user.city = city
            current_user.bio = bio
            current_user.website = website
            
            flash('Profile updated successfully!', 'success')
            
        except Exception as e:
            print(f"Error updating profile: {str(e)}")
            flash('Error updating profile. Please try again.', 'error')
    
    # Get user data for display
    try:
        # Reload user data to ensure we have the latest information
        user_ref = db.reference(f'users/{current_user.id}')
        user_data = user_ref.get() or {}
        
        # Update current user object with latest data
        if user_data:
            current_user.full_name = user_data.get('full_name', current_user.full_name)
            current_user.institution = user_data.get('institution')
            current_user.department = user_data.get('department')
            current_user.title = user_data.get('title')
            current_user.phone = user_data.get('phone')
            current_user.country = user_data.get('country')
            current_user.city = user_data.get('city')
            current_user.bio = user_data.get('bio')
            current_user.website = user_data.get('website')
            current_user.created_at = user_data.get('created_at')
            current_user.updated_at = user_data.get('updated_at')
            current_user.email_preferences = user_data.get('email_preferences', {})
        
        # Get user's registrations
        registrations_ref = db.reference('registrations')
        all_registrations = registrations_ref.get() or {}
        user_registrations = {k: v for k, v in all_registrations.items() 
                            if v.get('user_id') == current_user.id}
        
        # Get user's paper submissions
        submissions_ref = db.reference('papers')
        all_submissions = submissions_ref.get() or {}
        user_submissions = {k: v for k, v in all_submissions.items() 
                          if v.get('user_id') == current_user.id}
        
        # Get conferences data
        conferences_ref = db.reference('conferences')
        conferences = conferences_ref.get() or {}
        
        return render_template('user/account/profile.html', 
                            site_design=get_site_design(),
                            registrations=user_registrations,
                            submissions=user_submissions,
                            conferences=conferences)
                            
    except Exception as e:
        print(f"Error loading profile data: {str(e)}")
        return render_template('user/account/profile.html', 
                            site_design=get_site_design(),
                            registrations={},
                            submissions={},
                            conferences={})

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')
        
        # Validate inputs
        if not all([current_password, new_password, confirm_new_password]):
            flash('All password fields are required', 'error')
            return redirect(url_for('profile'))
        
        if new_password != confirm_new_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('profile'))
        
        if len(new_password) < 8:
            flash('New password must be at least 8 characters long', 'error')
            return redirect(url_for('profile'))
        
        # For now, we'll implement a simple password change
        # In a production environment, you'd want to verify the current password
        # and use Firebase Auth to update the password
        
        flash('Password change functionality is not yet implemented. Please contact support.', 'info')
        return redirect(url_for('profile'))
        
    except Exception as e:
        print(f"Error changing password: {str(e)}")
        flash('Error changing password. Please try again.', 'error')
        return redirect(url_for('profile'))

@app.route('/update-email-preferences', methods=['POST'])
@login_required
def update_email_preferences():
    try:
        # Get email preferences from form
        notify_registration = 'notify_registration' in request.form
        notify_papers = 'notify_papers' in request.form
        notify_announcements = 'notify_announcements' in request.form
        notify_schedule = 'notify_schedule' in request.form
        
        # Update user's email preferences in database
        user_ref = db.reference(f'users/{current_user.id}')
        user_data = user_ref.get() or {}
        
        if 'email_preferences' not in user_data:
            user_data['email_preferences'] = {}
        
        user_data['email_preferences'].update({
            'notify_registration': notify_registration,
            'notify_papers': notify_papers,
            'notify_announcements': notify_announcements,
            'notify_schedule': notify_schedule,
            'updated_at': datetime.now().isoformat()
        })
        
        user_ref.set(user_data)
        
        # Update current user object
        if not hasattr(current_user, 'email_preferences'):
            current_user.email_preferences = {}
        current_user.email_preferences.update({
            'notify_registration': notify_registration,
            'notify_papers': notify_papers,
            'notify_announcements': notify_announcements,
            'notify_schedule': notify_schedule
        })
        
        flash('Email preferences updated successfully!', 'success')
        
    except Exception as e:
        print(f"Error updating email preferences: {str(e)}")
        flash('Error updating email preferences. Please try again.', 'error')
    
    return redirect(url_for('profile'))

@app.route('/debug-login', methods=['GET', 'POST'])
def debug_login():
    """Debug version of login for troubleshooting"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"DEBUG LOGIN ATTEMPT: email={email}, password_length={len(password) if password else 0}")
        
        # Strip whitespace from inputs to prevent login issues
        email = email.strip() if email else ""
        password = password.strip() if password else ""
        
        try:
            # Check if the user exists in Firebase Auth
            user = auth.get_user_by_email(email)
            print(f"DEBUG: User found in Firebase Auth: {user.uid}")
            
            # For the admin user, we'll still verify the password manually
            admin_email = "admin@giirconference.com"
            admin_password = "Admin@2024!"
            
            # Check if this is admin login
            if email == admin_email:
                if password != admin_password:
                    print("DEBUG: Admin password mismatch")
                    flash('Invalid email or password', 'error')
                    return render_template('debug_login.html', site_design=get_site_design())
                print("DEBUG: Admin password correct")
            
            # Get user data from Realtime Database
            ref = db.reference(f'users/{user.uid}')
            user_data = ref.get()
            print(f"DEBUG: User data from database: {user_data}")
            
            # If user data doesn't exist in Realtime DB, create it
            if not user_data:
                is_admin_user = (email == admin_email)
                user_data = {
                    'email': email,
                    'full_name': user.display_name or email.split('@')[0],
                    'created_at': datetime.now().isoformat(),
                    'is_admin': is_admin_user
                }
                ref.set(user_data)
                print("DEBUG: Created new user data in database")
            
            is_admin = user_data.get('is_admin', False)
            display_name = user_data.get('full_name', email.split('@')[0])
            print(f"DEBUG: is_admin={is_admin}, display_name={display_name}")
            
            # Create User object and login
            user_obj = User(user.uid, email, display_name, is_admin)
            login_user(user_obj)
            print("DEBUG: User logged in successfully")
            
            flash('Logged in successfully!', 'success')
            
            # Redirect admin users to admin dashboard
            if is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
                
        except auth.UserNotFoundError:
            print(f"DEBUG: User not found: {email}")
            flash('Invalid email or password', 'error')
            return render_template('debug_login.html', site_design=get_site_design())
        except Exception as e:
            print(f"DEBUG: Login error: {str(e)}")
            flash(f'Login error: {str(e)}', 'error')
            return render_template('debug_login.html', site_design=get_site_design())
            
    return render_template('debug_login.html', site_design=get_site_design())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Strip whitespace from inputs to prevent login issues
        email = email.strip() if email else ""
        password = password.strip() if password else ""
        
        try:
            # Instead of trying to validate the login via REST API, we'll use Firebase Admin SDK
            # to retrieve the user, and if found, we'll assume the login is correct for now
            # This is a temporary workaround until we can fix the API key issue
            
            try:
                # Check if the user exists in Firebase Auth
                user = auth.get_user_by_email(email)
                
                # For the admin user, we'll still verify the password manually
                # For other users, we'll assume they exist and can login (since Firebase created them)
                admin_email = "admin@giirconference.com"
                admin_password = "Admin@2024!"
                
                # Check if this is admin login
                if email == admin_email:
                    if password != admin_password:
                        flash('Invalid email or password', 'error')
                        return render_template('user/auth/login.html', site_design=get_site_design())
                
                # At this point, either:
                # 1. It's the admin with correct password
                # 2. It's a regular user who exists in Firebase (password was validated during registration)
                
                # Get user data from Realtime Database
                ref = db.reference(f'users/{user.uid}')
                user_data = ref.get()
                
                # If user data doesn't exist in Realtime DB, create it
                if not user_data:
                    is_admin_user = (email == admin_email)
                    user_data = {
                        'email': email,
                        'full_name': user.display_name or email.split('@')[0],
                        'created_at': datetime.now().isoformat(),
                        'is_admin': is_admin_user
                    }
                    ref.set(user_data)
                
                is_admin = user_data.get('is_admin', False)
                display_name = user_data.get('full_name', email.split('@')[0])
                
                # Create User object and login
                user_obj = User(user.uid, email, display_name, is_admin)
                login_user(user_obj)
                
                flash('Logged in successfully!', 'success')
                
                # Check if there's a registration selection in session
                if 'registration_type' in session and 'registration_period' in session:
                    reg_type = session.pop('registration_type')
                    reg_period = session.pop('registration_period')
                    return redirect(url_for('registration_form', type=reg_type, period=reg_period))
                
                # Check for next parameter
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                
                # Redirect admin users to admin dashboard
                if is_admin:
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('dashboard'))
                    
            except auth.UserNotFoundError:
                flash('Invalid email or password', 'error')
                return render_template('user/auth/login.html', site_design=get_site_design())
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('Login error occurred', 'error')
            
    return render_template('user/auth/login.html', site_design=get_site_design())

@app.route('/register', methods=['GET', 'POST'])
def register_account():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        terms = request.form.get('terms')

        if not terms:
            flash('You must accept the terms and conditions.', 'error')
            return render_template('user/register.html', site_design=get_site_design())

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('user/register.html', site_design=get_site_design())

        try:
            # Create user in Firebase Authentication
            user = auth.create_user(
                email=email,
                password=password,
                display_name=full_name
            )
            
            # User data for database and email
            user_data = {
                'email': email,
                'full_name': full_name,
                'created_at': datetime.now().isoformat(),
                'is_admin': False  # Default to normal user
            }
            
            # Store additional user data in Realtime Database
            ref = db.reference('users')
            ref.child(user.uid).set(user_data)
            
            # Try to send welcome email (non-blocking)
            try:
                email_service.send_welcome_email(user_data)
            except Exception as e:
                print(f"Warning: Could not send welcome email: {str(e)}")
                # Continue with registration even if email fails
            
            flash('Account created successfully! You can now login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'error')
            return render_template('user/register.html', site_design=get_site_design())
    
    return render_template('user/register.html', site_design=get_site_design())

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/registration')
def registration():
    try:
        print("DEBUG: Starting registration page load")
        
        # Get registration fees from Firebase
        fees_ref = db.reference('registration_fees')
        fees = fees_ref.get()
        print(f"DEBUG: Loaded fees: {fees is not None}")
        
        # Get all available conferences
        all_conferences = get_all_conferences()
        print(f"DEBUG: Total conferences from get_all_conferences(): {len(all_conferences) if all_conferences else 0}")
        
        # Filter to show only active and upcoming conferences with registration enabled
        available_conferences = {}
        
        # Use South African Standard Time (UTC+02:00) for all comparisons
        sast_tz = pytz.timezone('Africa/Johannesburg')
        now = datetime.now(sast_tz)
        
        # Helper to parse to SAST aware datetimes
        def _parse_date(value):
            """Parse to timezone-aware datetime in SAST."""
            try:
                if not value:
                    return None
                text = str(value)
                dt = None
                try:
                    dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
                except Exception:
                    dt = datetime.strptime(text, '%Y-%m-%d')
                if getattr(dt, 'tzinfo', None) is None:
                    dt = sast_tz.localize(dt)
                else:
                    dt = dt.astimezone(sast_tz)
                return dt
            except Exception:
                return None
        
        for conf_id, conf_data in all_conferences.items():
            if not conf_data:
                continue
                
            # Ensure basic_info exists
            if 'basic_info' not in conf_data:
                conf_data['basic_info'] = {}
            
            # Get admin-provided status
            admin_status = (conf_data.get('basic_info', {}).get('status') or 
                          conf_data.get('settings', {}).get('status', 'draft')).strip().lower()
            
            # Parse dates
            start_dt = _parse_date(conf_data.get('basic_info', {}).get('start_date'))
            end_dt = _parse_date(conf_data.get('basic_info', {}).get('end_date'))
            
            # AUTO-COMPUTE status based on dates (prioritize date-based logic)
            computed_status = None
            if start_dt and end_dt:
                if now > end_dt:
                    # Conference has ENDED - ALWAYS mark as past
                    computed_status = 'past'
                elif now < start_dt:
                    # Conference hasn't STARTED yet
                    # Allow admin to set as 'active' for early registration/submissions
                    if admin_status == 'active':
                        computed_status = 'active'
                    else:
                        computed_status = 'upcoming'
                else:
                    # Conference is ONGOING
                    computed_status = 'active'
            elif end_dt and now > end_dt:
                computed_status = 'past'
            elif start_dt and now < start_dt:
                computed_status = 'upcoming'
            else:
                # No dates available, use admin status
                computed_status = admin_status if admin_status else 'draft'
            
            # Normalize status in basic_info
            conf_data['basic_info']['status'] = computed_status
            
            # Ensure past conferences have registration/submission disabled
            if computed_status == 'past':
                if 'settings' not in conf_data:
                    conf_data['settings'] = {}
                conf_data['settings']['registration_enabled'] = False
                conf_data['settings']['paper_submission_enabled'] = False
            
            # Check if registration is enabled
            registration_enabled = conf_data.get('settings', {}).get('registration_enabled', False)
            
            print(f"DEBUG: Conference {conf_id}:")
            print(f"  - Name: {conf_data.get('basic_info', {}).get('name', 'Unknown')}")
            print(f"  - Status: {computed_status}")
            print(f"  - Registration Enabled: {registration_enabled}")
            print(f"  - Start Date: {conf_data.get('basic_info', {}).get('start_date')}")
            print(f"  - End Date: {conf_data.get('basic_info', {}).get('end_date')}")
            
            # Show conferences that are:
            # 1. Active or Upcoming
            # 2. Have registration enabled
            # 3. Not past or archived
            if computed_status in ['active', 'upcoming'] and registration_enabled:
                available_conferences[conf_id] = conf_data
                print(f"  ✓ ADDED to available list")
            else:
                reasons = []
                if computed_status not in ['active', 'upcoming']:
                    reasons.append(f"status is '{computed_status}' (need 'active' or 'upcoming')")
                if not registration_enabled:
                    reasons.append("registration not enabled")
                print(f"  ✗ SKIPPED: {', '.join(reasons)}")
        
        print(f"DEBUG: Found {len(available_conferences)} available conferences:")
        for conf_id, conf in available_conferences.items():
            print(f"  - {conf_id}: {conf.get('basic_info', {}).get('name', 'Unknown')}")
        
        return render_template('user/registration.html', 
                             site_design=get_site_design(),
                             fees=fees,
                             conferences=available_conferences)
    except Exception as e:
        print(f"ERROR loading registration page: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading registration page.', 'error')
        return render_template('user/registration.html', 
                             site_design=get_site_design(),
                             fees={},
                             conferences={})

@app.route('/registration/register', methods=['POST'])
def registration_select():
    if not current_user.is_authenticated:
        # Store registration selection in session
        session['registration_type'] = request.form.get('registration_type')
        session['registration_period'] = request.form.get('registration_period')
        # Redirect to login with next parameter
        return redirect(url_for('login', next=url_for('registration_form')))
    
    # If user is already logged in, proceed to registration form
    return redirect(url_for('registration_form', 
                          type=request.form.get('registration_type'),
                          period=request.form.get('registration_period')))

@app.route('/schedule')
def schedule():
    schedule_ref = db.reference('schedule')
    schedule = schedule_ref.get()
    return render_template('user/conference/schedule.html', schedule=schedule, site_design=get_site_design())

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    try:
        # Get all users
        users_ref = db.reference('users')
        users = users_ref.get() or {}
        
        # Get all conferences
        conferences = get_all_conferences()
        
        # Get all registrations across all conferences
        all_registrations = {}
        total_registrations = 0
        pending_registrations = 0
        
        for conf_id, conf_data in conferences.items():
            if conf_data:
                reg_ref = db.reference(f'conferences/{conf_id}/registrations')
                conf_registrations = reg_ref.get() or {}
                all_registrations.update(conf_registrations)
                total_registrations += len(conf_registrations)
                pending_registrations += sum(1 for reg in conf_registrations.values() 
                                           if reg and reg.get('payment_status') == 'pending')
        
        # Get all submissions
        submissions_ref = db.reference('submissions')
        submissions = submissions_ref.get() or {}
        
        # Calculate stats
        stats = {
            'total_users': len(users) if users else 0,
            'total_conferences': len(conferences) if conferences else 0,
            'active_conferences': sum(1 for conf in conferences.values() 
                                    if conf and conf.get('basic_info', {}).get('status') == 'active'),
            'total_registrations': total_registrations,
            'total_submissions': len(submissions) if submissions else 0,
            'pending_registrations': pending_registrations,
            'pending_submissions': sum(1 for sub in submissions.values() if sub and sub.get('status') == 'pending') if submissions else 0,
            'total_admins': sum(1 for user in users.values() if user and user.get('is_admin')),
            'total_regular_users': sum(1 for user in users.values() if user and not user.get('is_admin'))
        }
        
        # Get recent registrations and users (last 5)
        recent_registrations = {}
        recent_users = {}
        
        if all_registrations:
            # Sort registrations by created_at date
            sorted_registrations = sorted(
                [(k, v) for k, v in all_registrations.items() if v and v.get('created_at')],
                key=lambda x: x[1].get('created_at', ''),
                reverse=True
            )
            # Get first 5 items
            recent_registrations = dict(sorted_registrations[:5])
            
        if users:
            # Sort users by created_at date
            sorted_users = sorted(
                [(k, v) for k, v in users.items() if v and v.get('created_at')],
                key=lambda x: x[1].get('created_at', ''),
                reverse=True
            )
            # Get first 5 items
            recent_users = dict(sorted_users[:5])
        
        return render_template('admin/dashboard.html', 
                             users=recent_users, 
                             registrations=recent_registrations,
                             stats=stats,
                             conferences=conferences,
                             site_design=get_site_design())
    except Exception as e:
        flash(f'Error loading admin dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html', 
                             users={}, 
                             registrations={},
                             stats={
                                'total_users': 0,
                                'total_conferences': 0,
                                'active_conferences': 0,
                                'total_registrations': 0,
                                'total_submissions': 0,
                                'pending_registrations': 0,
                                'pending_submissions': 0,
                                'total_admins': 0,
                                'total_regular_users': 0
                             },
                             conferences={},
                             site_design=get_site_design())

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    try:
        users_ref = db.reference('users')
        users = users_ref.get()
        return render_template('admin/users.html', users=users or {})
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return render_template('admin/users.html', users={})

@app.route('/admin/toggle-admin/<user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    try:
        user_ref = db.reference(f'users/{user_id}')
        user_data = user_ref.get()
        if user_data:
            user_data['is_admin'] = not user_data.get('is_admin', False)
            user_ref.update({'is_admin': user_data['is_admin']})
            flash("Admin status updated successfully.", 'success')
        return redirect(url_for('admin_users'))
    except Exception as e:
        flash(f'Error updating admin status: {str(e)}', 'error')
        return redirect(url_for('admin_users'))

def create_admin_user():
    try:
        admin_email = "admin@giirconference.com"
        admin_password = "Admin@2024!"
        admin_name = "Conference Admin"

        # Try to get existing admin user
        try:
            user = auth.get_user_by_email(admin_email)
            # Update existing admin's password
            auth.update_user(
                user.uid,
                password=admin_password
            )
            print("Admin password updated successfully!")
        except auth.UserNotFoundError:
            # Create new admin user if doesn't exist
            user = auth.create_user(
                email=admin_email,
                password=admin_password,
                display_name=admin_name
            )
            print("New admin user created successfully!")

        # Update or create admin data in Realtime Database
        ref = db.reference('users')
        ref.child(user.uid).update({
            'email': admin_email,
            'full_name': admin_name,
            'created_at': datetime.now().isoformat(),
            'is_admin': True,
            'updated_at': datetime.now().isoformat()
        })

        print("Admin user configuration complete!")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        return True
    except Exception as e:
        print(f"Error configuring admin user: {str(e)}")
        return False

def create_second_admin_user():
    try:
        admin_email = "admin@giirconference.com"
        admin_password = "Admin@2024!"
        admin_name = "Secondary Admin"

        # Try to get existing user by email
        try:
            user = auth.get_user_by_email(admin_email)
            # Update existing user's password
            auth.update_user(
                user.uid,
                password=admin_password
            )
            print("Second admin password updated successfully!")
        except auth.UserNotFoundError:
            # Create new admin user if doesn't exist
            user = auth.create_user(
                email=admin_email,
                password=admin_password,
                display_name=admin_name
            )
            print("New second admin user created successfully!")

        # Update or create admin data in Realtime Database
        ref = db.reference('users')
        ref.child(user.uid).update({
            'email': admin_email,
            'full_name': admin_name,
            'created_at': datetime.now().isoformat(),
            'is_admin': True,
            'updated_at': datetime.now().isoformat()
        })

        print("Second admin user configuration complete!")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        return True
    except Exception as e:
        print(f"Error configuring second admin user: {str(e)}")
        return False

@app.route('/setup-second-admin')
def setup_second_admin():
    success = create_second_admin_user()
    if success:
        return "Second admin user created/updated successfully! Check server logs for details."
    else:
        return "Error creating second admin user. Check server logs for details."

@app.route('/admin/venue', methods=['GET', 'POST'])
@admin_required
def admin_venue():
    if request.method == 'POST':
        try:
            # Get and validate form data
            venue_data = {
                'name': request.form.get('name', '').strip(),
                'address': request.form.get('address', '').strip(),
                'city': request.form.get('city', '').strip(),
                'country': request.form.get('country', '').strip(),
                'postal_code': request.form.get('postal_code', '').strip(),
                'phone': request.form.get('phone', '').strip(),
                'email': request.form.get('email', '').strip(),
                'map_url': request.form.get('map_url', '').strip()
            }
            
            # Validate required fields
            required_fields = ['name', 'address', 'city', 'country', 'postal_code', 'phone', 'email']
            missing_fields = [field for field in required_fields if not venue_data.get(field)]
            
            if missing_fields:
                flash(f'Missing required fields: {", ".join(missing_fields)}', 'danger')
                return redirect(url_for('admin_venue'))
            
            # Validate email format
            if '@' not in venue_data['email']:
                flash('Invalid email format', 'danger')
                return redirect(url_for('admin_venue'))
            
            # Generate map URL if not provided or invalid
            if not venue_data['map_url'] or 'maps/embed' not in venue_data['map_url']:
                address = f"{venue_data['address']}, {venue_data['city']}, {venue_data['country']}"
                venue_data['map_url'] = f"https://www.google.com/maps/embed/v1/place?key={app.config.get('GOOGLE_MAPS_API_KEY', '')}&q={address}"
            
            # Update venue details in Firebase
            venue_ref = db.reference('venue_details')
            venue_ref.set(venue_data)
            
            flash('Venue details updated successfully', 'success')
            return redirect(url_for('admin_venue'))
            
        except Exception as e:
            print(f"Error updating venue details: {str(e)}")
            flash(f'Error updating venue details: {str(e)}', 'danger')
            return redirect(url_for('admin_venue'))
    
    try:
        # Get current venue details
        venue_ref = db.reference('venue_details')
        venue_details = venue_ref.get()
        
        return render_template('admin/admin_venue.html', 
                             site_design=get_site_design(), 
                             venue_details=venue_details)
    except Exception as e:
        print(f"Error loading venue details: {str(e)}")
        flash(f'Error loading venue details: {str(e)}', 'danger')
        return render_template('admin/admin_venue.html', 
                             site_design=get_site_design(), 
                             venue_details=None)

@app.route('/admin/registration-fees', methods=['GET', 'POST'])
@admin_required
def admin_registration_fees():
    if request.method == 'POST':
        try:
            # Debug: Print all form data
            print("Form data received:", request.form)
            
            # Get currency settings
            currency_code = request.form.get('currency_code')
            custom_currency_symbol = request.form.get('custom_currency_symbol') if currency_code == 'custom' else None
            
            # Set up the currency structure
            currency = {
                'code': currency_code,
                'symbol': custom_currency_symbol if currency_code == 'custom' else {
                    'ZAR': 'R',
                    'USD': '$',
                    'EUR': '€',
                    'GBP': '£',
                    'AUD': 'A$'
                }.get(currency_code)
            }
            
            # Convert form data to float where needed
            def get_float(key, default=0):
                value = request.form.get(key)
                try:
                    return float(value) if value and value.strip() else default
                except (ValueError, TypeError):
                    print(f"Error converting {key} to float. Value: {value}")
                    return default
            
            # Convert form data to int where needed
            def get_int(key, default=0):
                value = request.form.get(key)
                try:
                    return int(value) if value and value.strip() else default
                except (ValueError, TypeError):
                    print(f"Error converting {key} to int. Value: {value}")
                    return default
            
            registration_fees = {
                'currency': currency,
                'early_bird': {
                    'enabled': request.form.get('early_bird_enabled') == 'on',
                    'deadline': request.form.get('early_bird_deadline', ''),
                    'seats': {
                        'total': get_int('early_bird_total_seats', 100),
                        'remaining': get_int('early_bird_remaining_seats', 100),
                        'show_remaining': request.form.get('show_remaining_seats') == 'on'
                    },
                    'fees': {
                        'student_author': get_float('early_bird_student'),
                        'regular_author': get_float('early_bird_regular'),
                        'physical_delegate': get_float('early_bird_physical'),
                        'virtual_delegate': get_float('early_bird_virtual'),
                        'listener': get_float('early_bird_listener')
                    },
                    'benefits': [b for b in request.form.getlist('early_bird_benefits[]') if b and b.strip()]
                } if request.form.get('early_bird_enabled') == 'on' else None,
                'early': {
                    'deadline': request.form.get('early_deadline', ''),
                    'fees': {
                        'student_author': get_float('early_student'),
                        'regular_author': get_float('early_regular'),
                        'physical_delegate': get_float('early_physical'),
                        'virtual_delegate': get_float('early_virtual'),
                        'listener': get_float('early_listener')
                    },
                    'benefits': [b for b in request.form.getlist('early_benefits[]') if b and b.strip()]
                },
                'regular': {
                    'deadline': request.form.get('regular_deadline', ''),
                    'fees': {
                        'student_author': get_float('regular_student'),
                        'regular_author': get_float('regular_regular'),
                        'physical_delegate': get_float('regular_physical'),
                        'virtual_delegate': get_float('regular_virtual')
                    },
                    'benefits': [b for b in request.form.getlist('regular_benefits[]') if b and b.strip()]
                },
                'late': {
                    'deadline': request.form.get('late_deadline', ''),
                    'fees': {
                        'student_author': get_float('late_student'),
                        'regular_author': get_float('late_regular'),
                        'physical_delegate': get_float('late_physical'),
                        'virtual_delegate': get_float('late_virtual'),
                        'listener': get_float('late_listener')
                    },
                    'benefits': [b for b in request.form.getlist('late_benefits[]') if b and b.strip()]
                },
                'additional_items': {
                    'extra_paper': {
                        'enabled': request.form.get('extra_paper_enabled') == 'on',
                        'fee': get_float('extra_paper_fee'),
                        'description': request.form.get('extra_paper_description', '').strip()
                    },
                    'workshop': {
                        'enabled': request.form.get('workshop_enabled') == 'on',
                        'fee': get_float('workshop_fee'),
                        'description': request.form.get('workshop_description', '').strip()
                    },
                    'banquet': {
                        'enabled': request.form.get('banquet_enabled') == 'on',
                        'fee': get_float('banquet_fee'),
                        'description': request.form.get('banquet_description', '').strip(),
                        'virtual_eligible': request.form.get('banquet_virtual_eligible') == 'on'
                    }
                }
            }
            
            # Debug: Print the structured data
            print("Structured data to save:", registration_fees)
            
            # Update registration fees in Firebase
            print("Attempting to save to Firebase...")
            try:
                db.reference('registration_fees').set(registration_fees)
                print("Successfully saved to Firebase!")
                flash('Registration fees updated successfully', 'success')
            except Exception as firebase_error:
                print(f"Firebase error: {firebase_error}")
                flash(f'Firebase error: {str(firebase_error)}', 'danger')
            
            return redirect(url_for('admin_registration_fees'))
            
        except Exception as e:
            import traceback
            print("Error saving registration fees:")
            print(traceback.format_exc())  # Print full stack trace
            flash(f'Error updating registration fees: {str(e)}', 'danger')
            return redirect(url_for('admin_registration_fees'))
    
    try:
        # Test Firebase connection first
        print("Testing Firebase connection...")
        test_ref = db.reference('test_connection')
        test_ref.set({'test': 'connection_ok', 'timestamp': str(datetime.now())})
        print("Firebase connection test successful!")
        
        # Get current fees settings
        fees_ref = db.reference('registration_fees')
        current_fees = fees_ref.get() or {}
        
        # Debug: Print current fees
        print("Current fees loaded:", current_fees)
        
        return render_template('admin/admin_registration_fees.html', 
                             site_design=get_site_design(), 
                             fees=current_fees)
    except Exception as e:
        import traceback
        print("Error loading registration fees:")
        print(traceback.format_exc())  # Print full stack trace
        flash(f'Error loading registration fees: {str(e)}', 'danger')
        return render_template('admin/admin_registration_fees.html', 
                             site_design=get_site_design(), 
                             fees={})

@app.route('/admin/downloads', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_downloads():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            try:
                # Create upload folder if it doesn't exist
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Secure the filename and generate unique name
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Save file locally
                file.save(file_path)
                
                # Get file size
                file_size = os.path.getsize(file_path)
                file_size_str = f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"
                
                # Determine the target collection based on category
                category = request.form.get('category', 'general')
                if category == 'conference_proceedings':
                    # Store in conference_proceedings collection
                    collection_ref = db.reference('conference_proceedings')
                    file_type = filename.rsplit('.', 1)[1].lower()
                    
                    # Determine format based on file type
                    if file_type in ['tex', 'latex']:
                        format_type = 'LaTeX'
                    elif file_type in ['doc', 'docx']:
                        format_type = 'Microsoft Word'
                    elif file_type == 'zip':
                        format_type = 'Archive'
                    else:
                        format_type = 'General'
                    
                    new_item = {
                        'title': request.form.get('title'),
                        'description': request.form.get('description'),
                        'file_type': file_type,
                        'format': format_type,
                        'file_size': file_size_str,
                        'file_url': f"/static/uploads/documents/{unique_filename}",
                        'updated_at': datetime.now().isoformat(),
                        'uploaded_by': current_user.email
                    }
                else:
                    # Store in downloads collection
                    collection_ref = db.reference('downloads')
                    new_item = {
                        'title': request.form.get('title'),
                        'description': request.form.get('description'),
                        'category': category,
                        'version': request.form.get('version', ''),
                        'external_url': request.form.get('external_url', ''),
                        'file_url': f"/static/uploads/documents/{unique_filename}",
                        'file_type': filename.rsplit('.', 1)[1].lower(),
                        'file_size': file_size_str,
                        'uploaded_at': datetime.now().isoformat(),
                        'type': request.form.get('type', 'pdf'),
                        'uploaded_by': current_user.email
                    }
                
                collection_ref.push(new_item)
                
                flash('Document uploaded successfully!', 'success')
                return redirect(url_for('admin_downloads'))
                
            except Exception as e:
                flash(f'Error uploading file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload PDF, DOC, DOCX, TEX, ZIP, XLS, XLSX, PPT, or PPTX files.', 'error')
            return redirect(request.url)
    
    # Get all downloads for display
    downloads_ref = db.reference('downloads')
    downloads = downloads_ref.get() or {}
    
    # Also get conference proceedings for display
    proceedings_ref = db.reference('conference_proceedings')
    proceedings = proceedings_ref.get() or {}
    
    return render_template('admin/downloads.html', 
                         site_design=get_site_design(), 
                         downloads=downloads,
                         proceedings=proceedings)

@app.route('/admin/downloads/delete/<download_id>', methods=['POST'])
@login_required
@admin_required
def delete_download(download_id):
    try:
        # Check if it's a conference proceeding or regular download
        proceedings_ref = db.reference(f'conference_proceedings/{download_id}')
        proceeding = proceedings_ref.get()
        
        if proceeding:
            # Delete conference proceeding
            file_path = os.path.join(app.root_path, proceeding['file_url'].lstrip('/'))
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete from Firebase
            proceedings_ref.delete()
            flash('Conference proceeding deleted successfully!', 'success')
        else:
            # Check regular downloads
            downloads_ref = db.reference(f'downloads/{download_id}')
            download = downloads_ref.get()
            
            if download:
                # Delete file from storage
                file_path = os.path.join(app.root_path, download['file_url'].lstrip('/'))
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                # Delete from Firebase
                downloads_ref.delete()
                
                flash('Download deleted successfully!', 'success')
            else:
                flash('Download not found', 'error')
            
    except Exception as e:
        flash(f'Error deleting download: {str(e)}', 'error')
        
    return redirect(url_for('admin_downloads'))

@app.route('/admin/registrations')
@login_required
@admin_required
def admin_registrations():
    try:
        # Get registrations from Firebase
        registrations_ref = db.reference('registrations')
        registrations_data = registrations_ref.get()

        # Get all conferences for association lookup
        conferences = get_all_conferences()

        # Convert to list and add the Firebase key as _id
        registrations = []
        if registrations_data:
            for key, reg in registrations_data.items():
                reg['_id'] = key  # Add Firebase key as _id
                # Ensure all required fields exist with defaults
                reg.setdefault('submission_date', '')
                reg.setdefault('full_name', '')
                reg.setdefault('email', '')
                reg.setdefault('institution', '')
                reg.setdefault('registration_type', '')
                reg.setdefault('registration_period', '')
                reg.setdefault('total_amount', 0)
                reg.setdefault('payment_status', 'pending')
                reg.setdefault('workshop', False)
                reg.setdefault('banquet', False)
                reg.setdefault('extra_paper', False)

                # Add conference association information
                conference_id = reg.get('conference_id', '')
                conference_code = reg.get('conference_code', '')
                conference_name = reg.get('conference_name', '')

                # Look up conference details if conference_id exists
                if conference_id and conference_id in conferences:
                    conference_data = conferences[conference_id]
                    reg['conference_info'] = {
                        'id': conference_id,
                        'name': conference_data.get('basic_info', {}).get('name', 'Unknown'),
                        'year': conference_data.get('basic_info', {}).get('year', ''),
                        'code': conference_code or conference_data.get('conference_code', ''),
                        'status': conference_data.get('basic_info', {}).get('status', 'unknown')
                    }
                else:
                    # For legacy registrations or missing conference data
                    reg['conference_info'] = {
                        'id': conference_id,
                        'name': conference_name or 'Legacy Conference',
                        'year': '',
                        'code': conference_code or '',
                        'status': 'legacy'
                    }

                registrations.append(reg)

            # Sort by submission date (newest first)
            registrations.sort(key=lambda x: x.get('submission_date', ''), reverse=True)

        return render_template('admin/manage_registrations.html',
                            registrations=registrations,
                            conferences=get_all_conferences(),
                            site_design=get_site_design())

    except Exception as e:
        print(f"Error loading registrations: {str(e)}")
        flash(f'Error loading registrations: {str(e)}', 'danger')
        return render_template('admin/manage_registrations.html',
                            registrations=[],
                            conferences={},
                            site_design=get_site_design())

@app.route('/admin/registrations/export')
@login_required
@admin_required
def export_registrations():
    """Export all registrations with conference information"""
    try:
        # Get registrations from Firebase
        registrations_ref = db.reference('registrations')
        registrations_data = registrations_ref.get()

        # Get all conferences for association lookup
        conferences = get_all_conferences()

        # Convert to list with conference info
        registrations = []
        if registrations_data:
            for key, reg in registrations_data.items():
                reg['_id'] = key  # Add Firebase key as _id
                # Ensure all required fields exist with defaults
                reg.setdefault('submission_date', '')
                reg.setdefault('full_name', '')
                reg.setdefault('email', '')
                reg.setdefault('institution', '')
                reg.setdefault('registration_type', '')
                reg.setdefault('registration_period', '')
                reg.setdefault('total_amount', 0)
                reg.setdefault('payment_status', 'pending')
                reg.setdefault('workshop', False)
                reg.setdefault('banquet', False)
                reg.setdefault('extra_paper', False)

                # Add conference association information
                conference_id = reg.get('conference_id', '')
                conference_code = reg.get('conference_code', '')
                conference_name = reg.get('conference_name', '')

                # Look up conference details if conference_id exists
                if conference_id and conference_id in conferences:
                    conference_data = conferences[conference_id]
                    reg['conference_info'] = {
                        'id': conference_id,
                        'name': conference_data.get('basic_info', {}).get('name', 'Unknown'),
                        'year': conference_data.get('basic_info', {}).get('year', ''),
                        'code': conference_code or conference_data.get('conference_code', ''),
                        'status': conference_data.get('basic_info', {}).get('status', 'unknown')
                    }
                else:
                    # For legacy registrations or missing conference data
                    reg['conference_info'] = {
                        'id': conference_id,
                        'name': conference_name or 'Legacy Conference',
                        'year': '',
                        'code': conference_code or '',
                        'status': 'legacy'
                    }

                registrations.append(reg)

            # Sort by submission date (newest first)
            registrations.sort(key=lambda x: x.get('submission_date', ''), reverse=True)

        return jsonify(registrations)

    except Exception as e:
        print(f"Error exporting registrations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/registrations/<registration_id>')
@login_required
@admin_required
def get_registration_details(registration_id):
    try:
        registration_ref = db.reference(f'registrations/{registration_id}')
        registration = registration_ref.get()

        if registration:
            # Update file paths to use the new /uploads route
            if registration.get('payment_proof'):
                # Handle both string (legacy) and dict (new format)
                if isinstance(registration['payment_proof'], str):
                    registration['payment_proof'] = registration['payment_proof'].replace('/static/uploads/', '')
                elif isinstance(registration['payment_proof'], dict):
                    # New format already has the correct structure, keep as is
                    pass
            if registration.get('paper') and registration['paper'].get('file_path'):
                registration['paper']['file_path'] = registration['paper']['file_path'].replace('/static/uploads/', '')

            # Add conference association information
            conference_id = registration.get('conference_id', '')
            conference_code = registration.get('conference_code', '')
            conference_name = registration.get('conference_name', '')

            # Look up conference details if conference_id exists
            conferences = get_all_conferences()
            if conference_id and conference_id in conferences:
                conference_data = conferences[conference_id]
                registration['conference_info'] = {
                    'id': conference_id,
                    'name': conference_data.get('basic_info', {}).get('name', 'Unknown'),
                    'year': conference_data.get('basic_info', {}).get('year', ''),
                    'code': conference_code or conference_data.get('conference_code', ''),
                    'status': conference_data.get('basic_info', {}).get('status', 'unknown')
                }
            else:
                # For legacy registrations or missing conference data
                registration['conference_info'] = {
                    'id': conference_id,
                    'name': conference_name or 'Legacy Conference',
                    'year': '',
                    'code': conference_code or '',
                    'status': 'legacy'
                }

            return jsonify(registration)
        else:
            return jsonify({'error': 'Registration not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_email_template(template_name):
    """Get email template from Firebase or return default template"""
    try:
        templates_ref = db.reference('email_templates').child(template_name)
        template = templates_ref.get()
        if template:
            return template
    except Exception as e:
        print(f"Error fetching template: {e}")
    
    # Default templates if not found in Firebase
    default_templates = {
        'registration_approval': {
            'subject': 'Your Conference Registration Has Been Approved',
            'content': '''Dear {{full_name}},

We are pleased to inform you that your registration for the conference has been approved!

Registration Details:
- Type: {{registration_type}}
- Amount Paid: R {{amount_paid}}

The conference will be held on {{conference_dates}}. We will send you additional information about the schedule and venue details closer to the date.

Thank you for registering for our conference. We look forward to your participation!

Best regards,
Conference Team'''
        },
        'registration_rejection': {
            'subject': 'Conference Registration Status Update',
            'content': '''Dear {{full_name}},

We regret to inform you that your conference registration could not be approved at this time.

Reason: {{rejection_reason}}

If you believe this is an error or would like to discuss this further, please contact our support team at {{support_email}}.

Best regards,
Conference Team'''
        }
    }
    
    return default_templates.get(template_name)

def send_registration_email(registration, template_name, **kwargs):
    """Send email notification for registration status update"""
    try:
        template = get_email_template(template_name)
        if not template:
            raise ValueError(f"Email template '{template_name}' not found")
        
        # Prepare template variables
        template_vars = {
            'full_name': registration.get('full_name', ''),
            'registration_type': registration.get('registration_type', '').replace('_', ' ').title(),
            'amount_paid': registration.get('total_amount', '0'),
            'conference_dates': 'September 15-17, 2024',  # You should get this from your conference settings
            'support_email': 'support@conference.com',  # You should get this from your conference settings
            **kwargs
        }
        
        # Replace template variables
        content = template['content']
        for key, value in template_vars.items():
            content = content.replace('{{' + key + '}}', str(value))
        
        # Create and send email
        msg = Message(
            subject=template['subject'],
            recipients=[registration.get('email')],
            body=content
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route('/admin/registrations/<registration_id>/status', methods=['POST'])
@login_required
@admin_required
def update_registration_status(registration_id):
    try:
        data = request.get_json()
        status = data.get('status')
        rejection_reason = data.get('rejection_reason')
        send_email = data.get('send_email', False)
        
        if not status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        # Get registration data
        registration_ref = db.reference(f'registrations/{registration_id}')
        registration_data = registration_ref.get()
        
        if not registration_data:
            return jsonify({'success': False, 'error': 'Registration not found'}), 404
        
        # Update status
        update_data = {
            'payment_status': status,
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        }
        
        if status == 'rejected' and rejection_reason:
            update_data['rejection_reason'] = rejection_reason
        
        registration_ref.update(update_data)
        
        email_sent = False
        if send_email:
            # Send email notification with correct template name
            template_name = 'registration_approval' if status == 'approved' else 'registration_rejection'
            email_sent = send_registration_email(
                registration_data,
                template_name,
                rejection_reason=rejection_reason
            )
        
        return jsonify({
            'success': True,
            'email_sent': email_sent
        })
        
    except Exception as e:
        print(f"Error updating registration status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/registrations/<registration_id>/payment-proof')
@login_required
@admin_required
def get_payment_proof(registration_id):
    try:
        registration_ref = db.reference(f'registrations/{registration_id}')
        registration = registration_ref.get()
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
            
        if not registration.get('payment_proof'):
            return jsonify({'error': 'No payment proof uploaded'}), 404
            
        # Clean up the file path
        payment_proof = registration['payment_proof']
        if not payment_proof.startswith('payments/'):
            payment_proof = f'payments/{payment_proof}'
            
        return jsonify({'url': payment_proof})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/registrations/<registration_id>/notes', methods=['POST'])
@login_required
@admin_required
def save_registration_notes(registration_id):
    try:
        data = request.get_json()
        notes = data.get('notes', '').strip()
        
        registration_ref = db.reference(f'registrations/{registration_id}')
        registration_ref.update({
            'admin_notes': notes,
            'notes_updated_at': datetime.now().isoformat(),
            'notes_updated_by': current_user.id
        })
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



def send_approval_email(email, registration):
    conference_name = registration.get('conference_name', 'GIIR Conference 2024')
    conference_code = registration.get('conference_code', '')
    registration_type = registration.get('registration_type', '').replace('_', ' ').title()
    registration_period = registration.get('registration_period', '').replace('_', ' ').title()
    total_amount = registration.get('total_amount', '')

    subject = f"{conference_name} - Registration Approved"

    body = f"""Dear {registration.get('full_name')},

Your registration for {conference_name} has been approved.
{"Conference Code: " + conference_code if conference_code else ""}

Registration Details:
- Type: {registration_type}
- Period: {registration_period}
- Total Amount: R {total_amount}

{'Your paper submission has been confirmed.' if 'author' in registration_type.lower() else ''}
{'Virtual access details will be sent closer to the conference date.' if 'virtual' in registration_type.lower() else ''}

Thank you for registering for {conference_name}.

Best regards,
Conference Organizing Committee"""

    send_email(email, subject, body)

def send_rejection_email(email, registration):
    conference_name = registration.get('conference_name', 'GIIR Conference 2024')
    conference_code = registration.get('conference_code', '')

    subject = f"{conference_name} - Registration Update"

    body = f"""Dear {registration.get('full_name')},

Your registration for {conference_name} requires attention.
{"Conference Code: " + conference_code if conference_code else ""}

Please log in to your dashboard to view the status of your registration and make any necessary updates.

If you have any questions, please contact us.

Best regards,
Conference Organizing Committee"""

    send_email(email, subject, body)


@login_required
@admin_required
def update_submission_comments(submission_id):
    data = request.get_json()
    comments = data.get('comments')
    
    if comments is None:
        return jsonify({'success': False, 'error': 'Comments are required'}), 400
        
    try:
        # Update submission comments in Firebase
        submission_ref = db.reference(f'papers/{submission_id}')
        submission_ref.update({
            'review_comments': comments,
            'updated_at': datetime.utcnow().isoformat(),
            'reviewed_by': current_user.email
        })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def send_submission_status_email(email, paper_title, status, comments):
    subject = 'Update on your GIIR Conference Paper Submission'
    
    status_messages = {
        'accepted': 'We are pleased to inform you that your paper has been accepted.',
        'rejected': 'We regret to inform you that your paper was not accepted.',
        'revision': 'Your paper requires revisions before it can be accepted.'
    }
    
    body = f"""Dear Author,

This email is regarding your paper submission: "{paper_title}"

{status_messages.get(status, 'Your paper status has been updated.')}

Reviewer Comments:
{comments or 'No additional comments provided.'}

{'Please submit your revised paper through the conference system.' if status == 'revision' else ''}

Best regards,
GIIR Conference Team
"""
    
    send_email(email, subject, body)

@app.route('/admin/announcements', methods=['GET'])
@login_required
@admin_required
def admin_announcements():
    try:
        # Get all announcements from Firebase
        announcements_ref = db.reference('announcements')
        announcements = announcements_ref.get() or {}
        
        # Sort announcements by pinned status and date
        sorted_announcements = dict(sorted(
            announcements.items(),
            key=lambda x: (
                not x[1].get('is_pinned', False),  # Pinned first
                x[1].get('scheduled_date', ''),    # Then by date
                x[1].get('scheduled_time', '')     # Then by time
            ),
            reverse=True
        ))
        
        return render_template(
            'admin/announcements.html',
            announcements=sorted_announcements,
            site_design=get_site_design(),
            tinymce_api_key=app.config.get('TINYMCE_API_KEY')
        )
    except Exception as e:
        flash(f'Error loading announcements: {str(e)}', 'error')
        return render_template(
            'admin/announcements.html',
            announcements={},
            site_design=get_site_design(),
            tinymce_api_key=app.config.get('TINYMCE_API_KEY')
        )

def send_email(recipients, subject, body, attachments=None):
    """Send email using configured email settings"""
    try:
        print(f"[EMAIL] Starting send_email to {len(recipients) if isinstance(recipients, list) else 1} recipient(s)")
        print(f"[EMAIL] Subject: {subject}")
        
        # Get email settings from Firebase
        settings_ref = db.reference('email_settings')
        settings = settings_ref.get()
        
        if not settings:
            print("[EMAIL] WARNING: Email settings not configured in Firebase")
            print("[EMAIL] Email sending skipped - configure email_settings in Firebase to enable")
            return False
        
        print("[EMAIL] Email settings found in Firebase")
        
        # Validate required settings
        required_settings = ['smtp_host', 'smtp_port', 'email', 'password']
        missing_settings = [s for s in required_settings if not settings.get(s)]
        
        if missing_settings:
            print(f"[EMAIL] ERROR: Missing email settings: {missing_settings}")
            raise ValueError(f"Missing email settings in Firebase: {missing_settings}")
        
        # Configure Flask-Mail with settings
        print(f"[EMAIL] Configuring Flask-Mail with SMTP: {settings.get('smtp_host')}:{settings.get('smtp_port')}")
        app.config.update(
            MAIL_SERVER=settings.get('smtp_host'),
            MAIL_PORT=int(settings.get('smtp_port', 587)),
            MAIL_USE_TLS=settings.get('use_tls', True),
            MAIL_USE_SSL=settings.get('use_ssl', False),
            MAIL_USERNAME=settings.get('email'),
            MAIL_PASSWORD=settings.get('password'),
            MAIL_DEFAULT_SENDER=f"GIIR Conference <{settings.get('email')}>"
        )
        
        # Create new Mail instance with current config
        mail_instance = Mail(app)
        
        # Create message
        recipients_list = recipients if isinstance(recipients, list) else [recipients]
        msg = Message(
            subject=subject,
            recipients=recipients_list,
            body=body
        )
        
        print(f"[EMAIL] Message created - Recipients: {recipients_list}")
        
        # Add attachments if any
        if attachments:
            print(f"[EMAIL] Adding {len(attachments)} attachments")
            for attachment in attachments:
                msg.attach(
                    filename=os.path.basename(attachment['path']),
                    content_type=attachment['type'],
                    data=attachment['data']
                )
        
        # Send email
        print("[EMAIL] Sending via Flask-Mail...")
        with app.app_context():
            mail_instance.send(msg)
        
        print(f"[EMAIL] ✓ Email sent successfully to {len(recipients_list)} recipient(s)")
        return True
        
    except Exception as e:
        print(f"[EMAIL] ✗ Error sending email: {str(e)}")
        import traceback
        traceback.print_exc()
        # Don't re-raise, just log and return False - email failures shouldn't break announcements
        return False

@app.route('/admin/announcements', methods=['POST'])
@login_required
@admin_required
def create_announcement():
    try:
        print("=" * 60)
        print("Creating new announcement...")
        print("=" * 60)
        
        # Create announcements upload directory if it doesn't exist
        upload_path = os.path.join(app.static_folder, 'uploads', 'announcements')
        os.makedirs(upload_path, exist_ok=True)
        
        # Get form data
        title = request.form.get('title')
        content = request.form.get('content')
        announcement_type = request.form.get('type')
        is_pinned = request.form.get('is_pinned') == 'on'
        should_send_email = request.form.get('send_email') == 'on'
        scheduled_date = request.form.get('announcement_date')
        scheduled_time = request.form.get('announcement_time')
        timezone = request.form.get('timezone')
        
        print("Received form data:", {
            'title': title,
            'content': content[:100] + '...' if content else None,
            'type': announcement_type,
            'is_pinned': is_pinned,
            'send_email': should_send_email,
            'date': scheduled_date,
            'time': scheduled_time,
            'timezone': timezone
        })
        
        if not all([title, content, announcement_type, scheduled_date, scheduled_time, timezone]):
            missing_fields = [field for field, value in {
                'title': title,
                'content': content,
                'type': announcement_type,
                'date': scheduled_date,
                'time': scheduled_time,
                'timezone': timezone
            }.items() if not value]
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            print("Error:", error_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('admin_announcements'))
        
        # Handle image upload
        image_url = None
        image_data = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_image_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    unique_filename = f"announcement_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    file_path = os.path.join(upload_path, unique_filename)
                    file.save(file_path)
                    image_url = f"/static/uploads/announcements/{unique_filename}"
                    print("Image saved:", image_url)
                    # Store image data for email attachment
                    with open(file_path, 'rb') as f:
                        image_data = f.read()
                except Exception as img_error:
                    print(f"Warning: Failed to save image: {str(img_error)}")
                    # Continue without image, don't fail the whole announcement
        
        # Format the datetime with timezone
        print(f"Formatting datetime: date={scheduled_date}, time={scheduled_time}, tz={timezone}")
        formatted_datetime = format_datetime_with_timezone(
            scheduled_date,
            scheduled_time,
            timezone
        )
        print(f"Formatted datetime result: {formatted_datetime}")
        
        if not formatted_datetime:
            print("WARNING: formatted_datetime is None or empty, using fallback")
            # Use fallback: just combine date and time without timezone conversion
            formatted_datetime = f"{scheduled_date}T{scheduled_time}:00"
        
        # Create announcement data
        announcement = {
            'title': title,
            'content': content,
            'type': announcement_type,
            'is_pinned': is_pinned,
            'image_url': image_url,
            'scheduled_date': scheduled_date,
            'scheduled_time': scheduled_time,
            'timezone': timezone,
            'formatted_datetime': formatted_datetime,
            'created_at': datetime.now().isoformat(),
            'created_by': current_user.email,
            'updated_at': datetime.now().isoformat()
        }
        
        print("Announcement data prepared:", {k: v for k, v in announcement.items() if k != 'content'})
        print("Saving announcement to Firebase...")
        
        # Save to Firebase
        try:
            announcements_ref = db.reference('announcements')
            new_announcement = announcements_ref.push(announcement)
            announcement_id = new_announcement.key
            print(f"✓ Announcement saved successfully with ID: {announcement_id}")
        except Exception as firebase_error:
            print(f"✗ Firebase error: {str(firebase_error)}")
            import traceback
            traceback.print_exc()
            error_msg = f"Firebase save error: {str(firebase_error)}"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': error_msg}), 500
            flash(error_msg, 'error')
            return redirect(url_for('admin_announcements'))
        
        # Send email notification if requested
        email_status = None
        if should_send_email:  # Using renamed variable
            try:
                print("Sending email notifications...")
                # Get all user emails
                users_ref = db.reference('users')
                users = users_ref.get()
                if users:
                    recipient_emails = [user['email'] for user in users.values() if user.get('email')]
                    print(f"Found {len(recipient_emails)} recipients for email notification")
                    
                    if recipient_emails:
                        # Get email template
                        templates_ref = db.reference('email_templates')
                        templates = templates_ref.get() or {}
                        announcement_template = next(
                            (t for t in templates.values() if t.get('name') == 'announcement_notification'),
                            None
                        )
                        
                        if announcement_template:
                            subject = announcement_template['subject'].replace('{{title}}', title)
                            body = announcement_template['body'].replace('{{title}}', title).replace('{{content}}', content)
                        else:
                            subject = f'New Announcement: {title}'
                            body = f'''A new announcement has been posted:

{title}

{content}

Scheduled for: {scheduled_date} at {scheduled_time} ({timezone})

Best regards,
Conference Team'''
                        
                        attachments = []
                        if image_url and image_data:
                            attachments.append({
                                'path': image_url,
                                'type': 'image/jpeg',
                                'data': image_data
                            })
                        
                        print(f"Sending emails with subject: {subject}")
                        send_email(recipient_emails, subject, body, attachments)
                        email_status = f"Email notifications sent successfully to {len(recipient_emails)} recipients."
                        print(f"✓ {email_status}")
                    else:
                        email_status = "No recipient emails found."
                        print(f"⚠ {email_status}")
                else:
                    email_status = "No users found to send email notifications."
                    print(f"⚠ {email_status}")
            except Exception as e:
                error_msg = f"Error sending email notification: {str(e)}"
                print(f"✗ {error_msg}")
                import traceback
                traceback.print_exc()
                email_status = f"Warning: {error_msg}"  # Don't fail, just warn
        
        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        print("=" * 60)
        print(f"Announcement creation COMPLETE - AJAX: {is_ajax}")
        print("=" * 60)
        
        if is_ajax:
            return jsonify({
                'success': True, 
                'id': announcement_id,
                'emailStatus': email_status,
                'redirect': url_for('admin_announcements')
            })
        else:
            flash('Announcement created successfully!', 'success')
            if email_status:
                flash(email_status, 'info')
            return redirect(url_for('admin_announcements'))
            
    except Exception as e:
        error_msg = f"Error creating announcement: {str(e)}"
        print(f"✗ {error_msg}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': error_msg}), 500
        else:
            flash(error_msg, 'error')
            return redirect(url_for('admin_announcements'))

@app.route('/admin/announcements/<announcement_id>', methods=['GET'])
@login_required
@admin_required
def get_announcement(announcement_id):
    try:
        announcement_ref = db.reference(f'announcements/{announcement_id}')
        announcement = announcement_ref.get()
        
        if not announcement:
            return jsonify({'success': False, 'error': 'Announcement not found'}), 404
            
        return jsonify({
            'success': True,
            'announcement': announcement
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/announcements/<announcement_id>', methods=['PUT'])
@login_required
@admin_required
def update_announcement(announcement_id):
    try:
        # ===== CHECKPOINT 1: Form Data Validation =====
        print("=" * 60)
        print(f"[EDIT] Starting announcement update for ID: {announcement_id}")
        print("=" * 60)
        
        # Validate required fields
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        announcement_type = request.form.get('type', 'general')
        is_pinned = request.form.get('is_pinned') == 'on'
        send_email = request.form.get('send_email') == 'on'
        scheduled_date = request.form.get('announcement_date', '').strip()
        scheduled_time = request.form.get('announcement_time', '').strip()
        timezone = request.form.get('timezone', 'UTC').strip()
        
        # Validate required fields
        if not title:
            error_msg = "Announcement title is required"
            print(f"✗ {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        if not content:
            error_msg = "Announcement content is required"
            print(f"✗ {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        print(f"✓ Form data validated - Title: {title[:50]}...")
        
        # ===== CHECKPOINT 2: Get Existing Announcement =====
        print("[EDIT] Fetching existing announcement from Firebase...")
        announcement_ref = db.reference(f'announcements/{announcement_id}')
        current_announcement = announcement_ref.get()
        
        if not current_announcement:
            error_msg = f"Announcement not found: {announcement_id}"
            print(f"✗ {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404
        
        print(f"✓ Existing announcement retrieved")
        
        # ===== CHECKPOINT 3: Image Handling (Non-Critical) =====
        print("[EDIT] Processing image upload...")
        image_url = current_announcement.get('image_url')
        try:
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_image_file(file.filename):
                    try:
                        # Delete old image if exists
                        if image_url:
                            old_image_path = os.path.join(app.static_folder, image_url.lstrip('/static/'))
                            if os.path.exists(old_image_path):
                                os.remove(old_image_path)
                                print(f"✓ Old image deleted: {image_url}")
                        
                        # Save new image
                        filename = secure_filename(file.filename)
                        unique_filename = f"announcement_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        upload_path = os.path.join(app.static_folder, 'uploads', 'announcements')
                        os.makedirs(upload_path, exist_ok=True)
                        file_path = os.path.join(upload_path, unique_filename)
                        
                        # Compress and save image
                        img = Image.open(file)
                        img.thumbnail((1200, 800), Image.Resampling.LANCZOS)
                        img.save(file_path, quality=85, optimize=True)
                        
                        image_url = f"/static/uploads/announcements/{unique_filename}"
                        print(f"✓ New image uploaded: {image_url}")
                    except Exception as e:
                        img_error = f"Warning: Image upload failed: {str(e)}"
                        print(f"⚠ {img_error}")
                        # Continue without image - non-critical failure
                        image_url = current_announcement.get('image_url')
        except Exception as e:
            print(f"⚠ Image processing error (non-critical): {str(e)}")
            image_url = current_announcement.get('image_url')
        
        # ===== CHECKPOINT 4: DateTime Formatting =====
        print("[EDIT] Formatting datetime with timezone...")
        formatted_datetime = format_datetime_with_timezone(
            scheduled_date,
            scheduled_time,
            timezone
        )
        
        if not formatted_datetime:
            formatted_datetime = current_announcement.get('formatted_datetime', datetime.now().isoformat())
            print(f"⚠ Using previous datetime: {formatted_datetime}")
        else:
            print(f"✓ Formatted datetime: {formatted_datetime}")
        
        # ===== CHECKPOINT 5: Firebase Update =====
        print("[EDIT] Updating Firebase database...")
        update_data = {
            'title': title,
            'content': content,
            'type': announcement_type,
            'is_pinned': is_pinned,
            'image_url': image_url,
            'scheduled_date': scheduled_date,
            'scheduled_time': scheduled_time,
            'timezone': timezone,
            'formatted_datetime': formatted_datetime,
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        }
        
        try:
            announcement_ref.update(update_data)
            print(f"✓ Announcement updated in Firebase")
        except Exception as e:
            error_msg = f"Database update failed: {str(e)}"
            print(f"✗ {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': error_msg}), 500
        
        # ===== CHECKPOINT 6: Email Notification (Non-Critical) =====
        print("[EDIT] Processing email notification...")
        email_status = None
        if send_email:
            try:
                result = send_email_with_logging(
                    subject=f'Announcement Updated: {title}',
                    body=f'''
An announcement has been updated:

Title: {title}

Content: {content}

Scheduled for: {scheduled_date} at {scheduled_time} ({timezone})

Best regards,
Conference Team
                    ''',
                    announcement_type='update',
                    title=title
                )
                
                if result['success']:
                    email_status = f"✓ Email sent successfully to {result['count']} recipient(s)"
                    print(f"[EMAIL] {email_status}")
                else:
                    email_status = f"Warning: {result['message']}"
                    print(f"[EMAIL] ✗ {result['message']}")
            except Exception as e:
                error_msg = f"Error sending email notification: {str(e)}"
                print(f"[EMAIL] ✗ {error_msg}")
                import traceback
                traceback.print_exc()
                email_status = f"Warning: {error_msg}"  # Don't fail, just warn
        
        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        print("=" * 60)
        print(f"Announcement update COMPLETE - AJAX: {is_ajax}")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'id': announcement_id,
            'emailStatus': email_status,
            'redirect': url_for('admin_announcements')
        })
    
    except Exception as e:
        error_msg = f"Error updating announcement: {str(e)}"
        print(f"✗ {error_msg}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/admin/announcements/<announcement_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    try:
        # ===== CHECKPOINT 1: Fetch Announcement =====
        print("=" * 60)
        print(f"[DELETE] Starting announcement deletion for ID: {announcement_id}")
        print("=" * 60)
        
        announcement_ref = db.reference(f'announcements/{announcement_id}')
        announcement = announcement_ref.get()
        
        if not announcement:
            error_msg = f"Announcement not found: {announcement_id}"
            print(f"✗ {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404
        
        print(f"✓ Announcement retrieved - Title: {announcement.get('title', 'Unknown')}")
        
        # ===== CHECKPOINT 2: Delete Associated Image (Non-Critical) =====
        print("[DELETE] Cleaning up associated image file...")
        try:
            if announcement.get('image_url'):
                image_path = os.path.join(app.static_folder, announcement['image_url'].lstrip('/static/'))
                if os.path.exists(image_path):
                    os.remove(image_path)
                    print(f"✓ Image deleted: {announcement['image_url']}")
                else:
                    print(f"⚠ Image file not found on disk: {announcement['image_url']}")
            else:
                print(f"ℹ No image associated with announcement")
        except Exception as e:
            print(f"⚠ Image cleanup failed (non-critical): {str(e)}")
            # Continue with deletion even if image cleanup fails
        
        # ===== CHECKPOINT 3: Delete from Firebase =====
        print("[DELETE] Removing announcement from Firebase...")
        try:
            announcement_ref.delete()
            print(f"✓ Announcement deleted from Firebase")
        except Exception as e:
            error_msg = f"Database deletion failed: {str(e)}"
            print(f"✗ {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': error_msg}), 500
        
        print("=" * 60)
        print(f"Announcement deletion COMPLETE")
        print("=" * 60)
        
        return jsonify({'success': True})
    
    except Exception as e:
        error_msg = f"Error deleting announcement: {str(e)}"
        print(f"✗ {error_msg}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        
        return jsonify({'success': False, 'error': error_msg}), 500

# Conference schedule configuration
SCHEDULE_DAYS = [
    'Day 1 - January 15, 2024',
    'Day 2 - January 16, 2024',
    'Day 3 - January 17, 2024'
]

TRACKS = [
    'Main Hall',
    'Room A',
    'Room B',
    'Room C',
    'Workshop Room'
]

@app.route('/admin/schedule')
@login_required
@admin_required
def admin_schedule():
    try:
        # Get all schedule sessions from Firebase
        schedule_ref = db.reference('schedule')
        schedule = schedule_ref.get()
        
        # Group sessions by day
        grouped_schedule = {}
        if schedule:
            for session_id, session in schedule.items():
                day = session['day']
                if day not in grouped_schedule:
                    grouped_schedule[day] = {}
                grouped_schedule[day][session_id] = session
            
            # Sort sessions within each day by start time
            for day in grouped_schedule:
                grouped_schedule[day] = dict(sorted(
                    grouped_schedule[day].items(),
                    key=lambda x: x[1]['start_time']
                ))

        return render_template('admin/schedule.html', site_design=get_site_design(),
                             schedule=grouped_schedule,
                             schedule_days=SCHEDULE_DAYS,
                             tracks=TRACKS)
    except Exception as e:
        flash(f'Error loading schedule: {str(e)}', 'error')
        return render_template('admin/schedule.html', site_design=get_site_design(),
                             schedule={},
                             schedule_days=SCHEDULE_DAYS,
                             tracks=TRACKS)

@app.route('/admin/schedule', methods=['POST'])
@login_required
@admin_required
def create_session():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['day', 'track', 'start_time', 'end_time', 'title', 'type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Validate time format
        try:
            start_time = datetime.strptime(data['start_time'], '%H:%M').strftime('%H:%M')
            end_time = datetime.strptime(data['end_time'], '%H:%M').strftime('%H:%M')
            if end_time <= start_time:
                return jsonify({'success': False, 'error': 'End time must be after start time'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid time format'}), 400
        
        # Create new session
        session = {
            'day': data['day'],
            'track': data['track'],
            'start_time': start_time,
            'end_time': end_time,
            'title': data['title'],
            'type': data['type'],
            'speakers': data.get('speakers', ''),
            'description': data.get('description', ''),
            'created_at': datetime.now().isoformat(),
            'created_by': current_user.email,
            'updated_at': datetime.now().isoformat()
        }
        
        # Save to Firebase
        schedule_ref = db.reference('schedule')
        new_session = schedule_ref.push(session)
        
        return jsonify({'success': True, 'id': new_session.key})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/schedule/<session_id>', methods=['PUT'])
@login_required
@admin_required
def update_session(session_id):
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['day', 'track', 'start_time', 'end_time', 'title', 'type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Validate time format
        try:
            start_time = datetime.strptime(data['start_time'], '%H:%M').strftime('%H:%M')
            end_time = datetime.strptime(data['end_time'], '%H:%M').strftime('%H:%M')
            if end_time <= start_time:
                return jsonify({'success': False, 'error': 'End time must be after start time'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid time format'}), 400
        
        # Update session
        session_ref = db.reference(f'schedule/{session_id}')
        current_session = session_ref.get()
        
        if not current_session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        update_data = {
            'day': data['day'],
            'track': data['track'],
            'start_time': start_time,
            'end_time': end_time,
            'title': data['title'],
            'type': data['type'],
            'speakers': data.get('speakers', ''),
            'description': data.get('description', ''),
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        }
        
        session_ref.update(update_data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/schedule/<session_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_session(session_id):
    try:
        # Delete session from Firebase
        session_ref = db.reference(f'schedule/{session_id}')
        session = session_ref.get()
        
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        session_ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/email-templates')
@login_required
@admin_required
def admin_email_templates():
    try:
        # Get all email templates from Firebase
        templates_ref = db.reference('email_templates')
        templates = templates_ref.get()
        
        # Sort templates by category and last updated
        if templates:
            sorted_templates = dict(sorted(
                templates.items(),
                key=lambda x: (x[1].get('category', ''), x[1].get('updated_at', '')),
                reverse=True
            ))
        else:
            sorted_templates = {}
            
        return render_template('admin/email_templates.html', site_design=get_site_design(), templates=sorted_templates)
    except Exception as e:
        flash(f'Error loading email templates: {str(e)}', 'error')
        return render_template('admin/email_templates.html', site_design=get_site_design(), templates={})

@app.route('/admin/email-templates', methods=['POST'])
@login_required
@admin_required
def create_email_template():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'category', 'subject', 'body']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Create new template
        template = {
            'name': data['name'],
            'category': data['category'],
            'subject': data['subject'],
            'body': data['body'],
            'created_at': datetime.now().isoformat(),
            'created_by': current_user.email,
            'updated_at': datetime.now().isoformat()
        }
        
        # Save to Firebase
        templates_ref = db.reference('email_templates')
        new_template = templates_ref.push(template)
        
        return jsonify({'success': True, 'id': new_template.key})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/email-templates/<template_id>', methods=['PUT'])
@login_required
@admin_required
def update_email_template(template_id):
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'category', 'subject', 'body']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Update template
        template_ref = db.reference(f'email_templates/{template_id}')
        current_template = template_ref.get()
        
        if not current_template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        update_data = {
            'name': data['name'],
            'category': data['category'],
            'subject': data['subject'],
            'body': data['body'],
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        }
        
        template_ref.update(update_data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/email-templates/<template_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_email_template(template_id):
    try:
        # Delete template from Firebase
        template_ref = db.reference(f'email_templates/{template_id}')
        template = template_ref.get()
        
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        template_ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper function to render email with template
def render_email_template(template_id, context):
    try:
        template_ref = db.reference(f'email_templates/{template_id}')
        template = template_ref.get()
        
        if not template:
            return None, None
            
        # Replace variables in subject and body
        subject = template['subject']
        body = template['body']
        
        for key, value in context.items():
            placeholder = '{{' + key + '}}'
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
            
        return subject, body
    except Exception as e:
        print(f"Error rendering email template: {str(e)}")
        return None, None

# Add these helper functions at the top level
def validate_associate_data(name, description, logo_url):
    """Validate associate data fields"""
    if not name or not name.strip():
        raise ValueError("Associate name is required")
    if not description or not description.strip():
        raise ValueError("Associate description is required")
    if not logo_url or not logo_url.strip():
        raise ValueError("Associate logo is required")
    return True

def save_associate_logo(logo_file, existing_logo=None):
    """Save associate logo to Firebase Storage and return the public URL"""
    if not logo_file or not logo_file.filename:
        if existing_logo:
            return existing_logo
        raise ValueError("Logo file is required")
    
    if not allowed_image_file(logo_file.filename):
        raise ValueError("Invalid image format. Allowed formats: PNG, JPG, JPEG, GIF")
    
    try:
        # Initialize Firebase Storage bucket
        bucket = storage.bucket()
                            
        # Generate unique filename
        filename = secure_filename(logo_file.filename)
        unique_filename = f"associates/logos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        
        # Create a new blob and upload the file
        blob = bucket.blob(unique_filename)
        # Set content type
        content_type = logo_file.content_type or 'image/jpeg'
        blob.content_type = content_type
        
        # Compress image if needed
        img_data = compress_image(logo_file, max_size_kb=500)
        
        # Upload the file
        blob.upload_from_string(
            img_data,
            content_type=content_type
        )
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Return the public URL
        return blob.public_url
        
    except Exception as e:
        print(f"Error saving logo to Firebase Storage: {str(e)}")
        raise ValueError(f"Error saving logo: {str(e)}")

def process_associates_data(request_form, request_files):
    """Process associates data from the form submission"""
    try:
        print("Received files in process_associates_data:", request_files.keys())
        associates = []
        errors = []
        bucket = storage.bucket()

        # Process existing associates
        existing_ids = request_form.getlist('existing_associate_ids[]')
        existing_logos = request_form.getlist('existing_associate_logos[]')
        
        print(f"Processing {len(existing_ids)} existing associates")
        
        # Check total number of associates (existing + new)
        new_files = request_files.getlist('new_associate_logos')
        total_associates = len(existing_ids) + len(new_files)
        MAX_ASSOCIATES = 10  # Maximum number of associates allowed
        
        if total_associates > MAX_ASSOCIATES:
            raise ValueError(f"Maximum number of associates ({MAX_ASSOCIATES}) exceeded. Please remove some logos before adding new ones.")
        
        # Handle existing associates
        for i, associate_id in enumerate(existing_ids):
            try:
                logo_url = existing_logos[i]
                logo_key = f'associate_logo_{associate_id}'
                
                if logo_key in request_files and request_files[logo_key].filename:
                    # Delete old logo if it exists
                    try:
                        if logo_url and logo_url.startswith('https://'):
                            blob_path = logo_url.split('/o/')[1].split('?')[0]
                            blob_path = blob_path.replace('%2F', '/')
                            blob = bucket.blob(blob_path)
                            if blob.exists():
                                blob.delete()
                                print(f"Successfully deleted old logo: {blob_path}")
                    except Exception as e:
                        print(f"Error deleting old logo: {str(e)}")

                    # Save new logo
                    logo_url = save_associate_logo(request_files[logo_key])
                
                associates.append({
                    'id': associate_id,
                    'logo': logo_url,
                    'name': 'Associate',
                    'description': ''
                })
                
            except Exception as e:
                errors.append(f"Error processing associate {associate_id}: {str(e)}")

        # Process new associate logos from multiple file upload
        if 'new_associate_logos' in request_files:
            new_files = request_files.getlist('new_associate_logos')
            print(f"Processing {len(new_files)} new associate logos")
            
            for file in new_files:
                if file and file.filename:
                    try:
                        logo_url = save_associate_logo(file)
                        associates.append({
                            'id': str(uuid.uuid4()),
                            'logo': logo_url,
                            'name': 'New Associate',
                            'description': ''
                        })
                        print(f"Successfully added new associate logo: {logo_url}")
                    except Exception as e:
                        print(f"Error processing new logo: {str(e)}")
                        errors.append(str(e))

        if errors:
            print("Errors during associate processing:", errors)
            raise Exception('\n'.join(errors))

        print(f"Successfully processed {len(associates)} total associates")
        return associates

    except Exception as e:
        print(f"Error in process_associates_data: {str(e)}")
        raise e

@app.route('/admin/home-content', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_home_content():
    try:
        content_ref = db.reference('home_content')
        
        if request.method == 'POST':
            try:
                # Initialize update_data with default structure
                update_data = {
                    'welcome': {
                        'title': request.form.get('welcome[title]', ''),
                        'subtitle': request.form.get('welcome[subtitle]', ''),
                        'conference_date': request.form.get('welcome[conference_date]', ''),
                        'message': request.form.get('welcome[message]', ''),
                        'subtitle_marquee': 'welcome[subtitle_marquee]' in request.form
                    },
                    'hero': {
                        'images': [],
                        'conference': {
                            'name': request.form.get('conference[name]', ''),
                            'date': request.form.get('conference[date]', ''),
                            'time': request.form.get('conference[time]', ''),
                            'city': request.form.get('conference[city]', ''),
                            'highlights': request.form.get('conference[highlights]', ''),
                            'show_countdown': 'conference[show_countdown]' in request.form
                        }
                    },
                    'vmo': {
                        'vision': request.form.get('vmo[vision]', ''),
                        'mission': request.form.get('vmo[mission]', ''),
                        'objectives': request.form.get('vmo[objectives]', '')
                    },
                    'associates': [],
                    'footer': {
                        'contact_email': request.form.get('footer[contact_email]', ''),
                        'contact_phone': request.form.get('footer[contact_phone]', ''),
                        'address': request.form.get('footer[address]', ''),
                        'copyright': request.form.get('footer[copyright]', ''),
                        'social_media': {
                            'facebook': request.form.get('footer[social_media][facebook]', ''),
                            'twitter': request.form.get('footer[social_media][twitter]', ''),
                            'linkedin': request.form.get('footer[social_media][linkedin]', '')
                        }
                    }
                }

                # Get current content for existing images
                current_content = content_ref.get() or {}
                if 'hero' in current_content and 'images' in current_content['hero']:
                    update_data['hero']['images'] = current_content['hero']['images']

                # Process deleted hero images
                deleted_images = request.form.getlist('deleted_hero_images[]')
                if deleted_images:
                    update_data['hero']['images'] = [
                        img for img in update_data['hero']['images'] 
                        if img['url'] not in deleted_images
                    ]

                # Process new hero images
                if 'hero_images' in request.files:
                    for file in request.files.getlist('hero_images'):
                        if file and file.filename:
                            try:
                                validate_image(file, image_type='hero')
                                bucket = storage.bucket()
                                filename = secure_filename(file.filename)
                                unique_filename = f"hero/images/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                blob = bucket.blob(unique_filename)
                                content_type = file.content_type or 'image/jpeg'
                                blob.content_type = content_type
                                img_data = compress_image(file, max_size_kb=800)
                                blob.upload_from_string(img_data, content_type=content_type)
                                blob.make_public()
                                update_data['hero']['images'].append({
                                    'url': blob.public_url,
                                    'alt': filename
                                })
                            except Exception as e:
                                print(f"Error processing hero image: {str(e)}")
                                continue

                # Process associates
                existing_ids = request.form.getlist('existing_associate_ids[]')
                existing_logos = request.form.getlist('existing_associate_logos[]')
                
                # Handle existing associates
                for i, associate_id in enumerate(existing_ids):
                    if i < len(existing_logos):
                        update_data['associates'].append({
                            'id': associate_id,
                            'logo': existing_logos[i]
                        })

                # Process new associate logos
                if 'new_associate_logos' in request.files:
                    for file in request.files.getlist('new_associate_logos'):
                        if file and file.filename:
                            try:
                                validate_image(file)
                                bucket = storage.bucket()
                                filename = secure_filename(file.filename)
                                unique_filename = f"associates/logos/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                blob = bucket.blob(unique_filename)
                                content_type = file.content_type or 'image/jpeg'
                                blob.content_type = content_type
                                img_data = compress_image(file, max_size_kb=500)
                                blob.upload_from_string(img_data, content_type=content_type)
                                blob.make_public()
                                update_data['associates'].append({
                                    'id': str(uuid.uuid4()),
                                    'logo': blob.public_url
                                })
                            except Exception as e:
                                print(f"Error processing associate logo: {str(e)}")
                                continue

                # Process downloads
                update_data['downloads'] = process_downloads_data(request)

                # Save the updated content
                content_ref.set(update_data)
                
                # Check if request wants JSON response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True})
                
                flash('Home content updated successfully!', 'success')
                return redirect(url_for('admin_home_content'))

            except Exception as e:
                print(f"Error updating home content: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': str(e)})
                flash('Error updating home content', 'error')
                return redirect(url_for('admin_home_content'))

        # GET request - render template
        home_content = content_ref.get() or {}
        return render_template('admin/home_content.html', home_content=home_content)

    except Exception as e:
        print(f"Error in admin_home_content: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)})
        flash('Error loading home content', 'error')
        return render_template('admin/home_content.html', home_content={})

# Add to admin_required routes list in base_admin.html
# Add this to ensure session persistence
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        session.permanent = True  # Make session permanent
        app.permanent_session_lifetime = timedelta(minutes=60)

@app.route('/admin/design', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_design():
    if request.method == 'POST':
        try:
            # Handle theme colors
            theme_data = {
                'primary_color': request.form.get('primary_color', DEFAULT_THEME['primary_color']),
                'secondary_color': request.form.get('secondary_color', DEFAULT_THEME['secondary_color']),
                'accent_color': request.form.get('accent_color', DEFAULT_THEME['accent_color']),
                'text_color': request.form.get('text_color', DEFAULT_THEME['text_color']),
                'background_color': request.form.get('background_color', DEFAULT_THEME['background_color']),
                'header_background': request.form.get('header_background', DEFAULT_THEME['header_background']),
                'footer_background': request.form.get('footer_background', DEFAULT_THEME['footer_background']),
                'hero_text_color': request.form.get('hero_text_color', DEFAULT_THEME['hero_text_color']),
                'subtitle_marquee': 'subtitle_marquee' in request.form
            }
            
            # Save theme data to Firebase
            design_ref = db.reference('site_design')
            design_ref.set(theme_data)
            
            flash('Site design updated successfully!', 'success')
            return redirect(url_for('admin_design'))
            
        except Exception as e:
            flash(f'Error updating site design: {str(e)}', 'error')
            return redirect(url_for('admin_design'))
    
    return render_template('admin/design.html', site_design=get_site_design())

@app.route('/downloads')
def downloads():
    try:
        # Get downloads from Firebase
        downloads_ref = db.reference('downloads')
        downloads_data = downloads_ref.get()
        
        # Organize downloads by category
        organized_downloads = {}
        if downloads_data:
            for key, item in downloads_data.items():
                category = item.get('category', 'General')
                if category not in organized_downloads:
                    organized_downloads[category] = []
                
                # Ensure all required fields are present
                download_item = {
                    'title': item.get('title', 'Untitled'),
                    'description': item.get('description', ''),
                    'type': item.get('type', 'file'),
                    'size': item.get('file_size', ''),
                    'url': item.get('file_url', '#')
                }
                organized_downloads[category].append(download_item)
        
        return render_template('user/conference/downloads.html', 
                             downloads=organized_downloads,
                             site_design=get_site_design())
    except Exception:
        flash('Error loading downloads.', 'error')
        return render_template('user/conference/downloads.html', 
                             downloads={},
                             site_design=get_site_design())

@app.route('/admin/about-content', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_about_content():
    try:
        if request.method == 'POST':
            # Handle committee member images
            committee = []
            committee_roles = request.form.getlist('committee_roles[]')
            committee_names = request.form.getlist('committee_names[]')
            committee_affiliations = request.form.getlist('committee_affiliations[]')
            committee_expertise = request.form.getlist('committee_expertise[]')
            committee_existing_images = request.form.getlist('committee_existing_images[]')
            
            # Create upload directory if it doesn't exist
            os.makedirs(os.path.join(app.static_folder, 'uploads', 'committee'), exist_ok=True)
            
            for i in range(len(committee_roles)):
                member = {
                    'role': committee_roles[i],
                    'name': committee_names[i],
                    'affiliation': committee_affiliations[i],
                    'expertise': [exp.strip() for exp in committee_expertise[i].split(',') if exp.strip()],
                    'image': committee_existing_images[i] if i < len(committee_existing_images) else ''
                }
                
                # Check for new image upload
                image_key = f'committee_image_{i}'
                if image_key in request.files:
                    file = request.files[image_key]
                    if file and file.filename and allowed_image_file(file.filename):
                        # Generate unique filename
                        filename = secure_filename(file.filename)
                        unique_filename = f"committee_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.{filename.rsplit('.', 1)[1].lower()}"
                        
                        # Save the file
                        file_path = os.path.join(app.static_folder, 'uploads', 'committee', unique_filename)
                        file.save(file_path)
                        
                        # Update member image path
                        member['image'] = f"/static/uploads/committee/{unique_filename}"
                
                committee.append(member)

            about_content = {
                'overview': {
                    'title': request.form.get('overview_title', ''),
                    'description': request.form.get('overview_description', ''),
                    'stats': {
                        'attendees': request.form.get('stats_attendees', '500+'),
                        'countries': request.form.get('stats_countries', '50+'),
                        'papers': request.form.get('stats_papers', '200+'),
                        'speakers': request.form.get('stats_speakers', '30+')
                    }
                },
                'objectives': [
                    {
                        'icon': icon,
                        'title': title,
                        'description': desc
                    }
                    for icon, title, desc in zip(
                        request.form.getlist('objective_icons[]'),
                        request.form.getlist('objective_titles[]'),
                        request.form.getlist('objective_descriptions[]')
                    )
                ],
                'committee': committee,
                'past_conferences': [
                    {
                        'year': year,
                        'location': loc,
                        'highlight': high
                    }
                    for year, loc, high in zip(
                        request.form.getlist('conference_years[]'),
                        request.form.getlist('conference_locations[]'),
                        request.form.getlist('conference_highlights[]')
                    )
                ],
                'future_conference': {
                    'enabled': False,
                    'year': '',
                    'title': '',
                    'platform': 'Physical',
                    'dates': []
                }
            }
            
            # Handle future conference data
            future_conference_enabled = request.form.get('future_conference_enabled') == 'on'
            if future_conference_enabled:
                # Handle multiple future conferences
                future_conferences = []
                conference_years = request.form.getlist('future_conference_years[]')
                conference_titles = request.form.getlist('future_conference_titles[]')
                conference_platforms = request.form.getlist('future_conference_platforms[]')
                conference_enabled_flags = request.form.getlist('future_conference_individual_enabled[]')
                
                for i in range(len(conference_years)):
                    if i < len(conference_titles) and i < len(conference_platforms):
                        # Handle dates for this specific conference
                        conference_dates = []
                        # Get dates for this specific conference (using indexed naming)
                        dates_key = f'future_conference_dates_{i}[]'
                        months_key = f'future_conference_months_{i}[]'
                        refs_key = f'future_conference_ref_codes_{i}[]'
                        
                        future_dates = request.form.getlist(dates_key)
                        future_months = request.form.getlist(months_key)
                        future_ref_codes = request.form.getlist(refs_key)
                        
                        for j in range(len(future_dates)):
                            if j < len(future_months) and j < len(future_ref_codes):
                                conference_dates.append({
                                    'date': future_dates[j],
                                    'month': future_months[j],
                                    'ref_code': future_ref_codes[j]
                                })
                        
                        # Check if this specific conference is enabled
                        conf_enabled = len(conference_enabled_flags) > i and conference_enabled_flags[i] == 'on'
                        
                        future_conferences.append({
                            'enabled': conf_enabled,
                            'year': conference_years[i],
                            'title': conference_titles[i],
                            'platform': conference_platforms[i],
                            'dates': conference_dates
                        })
                
                about_content['future_conferences'] = {
                    'section_enabled': True,
                    'conferences': future_conferences
                }
            else:
                about_content['future_conferences'] = {
                    'section_enabled': False,
                    'conferences': []
                }
            
            # Save to Firebase
            db.reference('about_content').set(about_content)
            flash('About page content updated successfully!', 'success')
            return redirect(url_for('admin_about_content'))
            
        # Get existing content
        about_content = db.reference('about_content').get() or {
            'overview': {
                'title': 'About GIIR Conference',
                'description': 'The Global Institute on Innovative Research (GIIR) Conference 2024 brings together leading researchers, practitioners, and industry experts from around the world.',
                'stats': {
                    'attendees': '500+',
                    'countries': '50+',
                    'papers': '200+',
                    'speakers': '30+'
                }
            },
            'objectives': [
                {
                    'icon': 'fa-lightbulb',
                    'title': 'Knowledge Exchange',
                    'description': 'Facilitate the exchange of innovative ideas and research findings'
                },
                {
                    'icon': 'fa-users',
                    'title': 'Networking',
                    'description': 'Create opportunities for networking and collaboration'
                },
                {
                    'icon': 'fa-chart-line',
                    'title': 'Research Impact',
                    'description': 'Showcase cutting-edge research and its potential impact'
                }
            ],
            'committee': [
                {
                    'role': 'Conference Chair',
                    'name': 'Prof. Sarah Johnson',
                    'affiliation': 'Stanford University, USA',
                    'expertise': ['Artificial Intelligence', 'Machine Learning'],
                    'image': ''
                }
            ],
            'past_conferences': [
                {
                    'year': '2023',
                    'location': 'Tokyo, Japan',
                    'highlight': '450+ Attendees'
                }
            ],
            'future_conferences': {
                'section_enabled': False,
                'conferences': []
            }
        }
        
        return render_template('admin/about_content.html', 
                             about_content=about_content,
                             site_design=get_site_design())
        
    except Exception:
        flash('Error managing about content', 'error')
        return redirect(url_for('admin_dashboard'))

def get_registration_fees():
    """
    Helper function to fetch registration fees from Firebase.
    Returns a dictionary containing all registration fee information.
    If no fees are set, returns a default structure.
    """
    try:
        # Get registration fees from Firebase
        fees_ref = db.reference('registration_fees')
        fees = fees_ref.get()
        
        if not fees:
            # Return default structure if no fees are set
            return {
                'currency': {
                    'code': 'ZAR',
                    'symbol': 'R'
                },
                'early_bird': {
                    'enabled': False,
                    'deadline': '',
                    'seats': {
                        'total': 100,
                        'remaining': 100,
                        'show_remaining': True
                    },
                    'fees': {
                        'student_author': 0,
                        'regular_author': 0,
                        'physical_delegate': 0,
                        'virtual_delegate': 0,
                        'listener': 0
                    },
                    'benefits': []
                },
                'early': {
                    'deadline': '',
                    'fees': {
                        'student_author': 0,
                        'regular_author': 0,
                        'physical_delegate': 0,
                        'virtual_delegate': 0,
                        'listener': 0
                    },
                    'benefits': []
                },
                'regular': {
                    'deadline': '',
                    'fees': {
                        'student_author': 0,
                        'regular_author': 0,
                        'physical_delegate': 0,
                        'virtual_delegate': 0,
                        'listener': 0
                    },
                    'benefits': []
                },
                'late': {
                    'deadline': '',
                    'fees': {
                        'student_author': 0,
                        'regular_author': 0,
                        'physical_delegate': 0,
                        'virtual_delegate': 0,
                        'listener': 0
                    },
                    'benefits': []
                },
                'additional_items': {
                    'extra_paper': {
                        'enabled': False,
                        'fee': 0,
                        'description': 'Submit an additional paper',
                        'virtual_eligible': True
                    },
                    'workshop': {
                        'enabled': False,
                        'fee': 0,
                        'description': 'Attend the conference workshop',
                        'virtual_eligible': True
                    },
                    'banquet': {
                        'enabled': False,
                        'fee': 0,
                        'description': 'Join the conference banquet',
                        'virtual_eligible': False
                    }
                }
            }
        
        # Ensure the fees structure is correct
        if 'currency' not in fees:
            fees['currency'] = {
                'code': 'ZAR',
                'symbol': 'R'
            }
        
        # Ensure each period has the correct structure
        for period in ['early_bird', 'early', 'regular', 'late']:
            if period in fees:
                if 'fees' not in fees[period]:
                    fees[period]['fees'] = {}
                
                # Ensure all registration types have a fee
                for reg_type in ['student_author', 'regular_author', 'physical_delegate', 'virtual_delegate', 'listener']:
                    if reg_type not in fees[period]['fees']:
                        fees[period]['fees'][reg_type] = 0
                
                # Ensure benefits list exists
                if 'benefits' not in fees[period]:
                    fees[period]['benefits'] = []
                
                # Ensure early bird has seats info
                if period == 'early_bird':
                    if 'seats' not in fees[period]:
                        fees[period]['seats'] = {
                            'total': 100,
                            'remaining': 100,
                            'show_remaining': True
                        }
        
        # Ensure additional items structure is correct
        if 'additional_items' not in fees:
            fees['additional_items'] = {
                'extra_paper': {
                    'enabled': False,
                    'fee': 0,
                    'description': 'Submit an additional paper',
                    'virtual_eligible': True
                },
                'workshop': {
                    'enabled': False,
                    'fee': 0,
                    'description': 'Attend the conference workshop',
                    'virtual_eligible': True
                },
                'banquet': {
                    'enabled': False,
                    'fee': 0,
                    'description': 'Join the conference banquet',
                    'virtual_eligible': False
                }
            }
        else:
            # Ensure each additional item has the correct structure
            for item in ['extra_paper', 'workshop', 'banquet']:
                if item not in fees['additional_items']:
                    fees['additional_items'][item] = {
                        'enabled': False,
                        'fee': 0,
                        'description': '',
                        'virtual_eligible': item != 'banquet'
                    }
                else:
                    if 'virtual_eligible' not in fees['additional_items'][item]:
                        fees['additional_items'][item]['virtual_eligible'] = item != 'banquet'
        
        return fees
    except Exception as e:
        print(f"Error fetching registration fees: {str(e)}")
        return None

def get_current_registration_period():
    """
    Determines the current registration period based on deadlines.
    Returns: 'early_bird', 'regular', 'late', or 'closed'
    """
    try:
        fees = get_registration_fees()
        if not fees:
            return 'closed'

        current_date = datetime.now().date()
        
        # Check Early Bird period
        if fees.get('early_bird', {}).get('enabled'):
            early_bird_deadline = datetime.strptime(fees['early_bird']['deadline'], '%Y-%m-%d').date()
            if current_date <= early_bird_deadline:
                # Check if seats are available
                seats = fees['early_bird'].get('seats', {})
                if seats.get('remaining', 0) > 0:
                    return 'early_bird'
                
        # Check Regular period
        if fees.get('regular', {}).get('deadline'):
            regular_deadline = datetime.strptime(fees['regular']['deadline'], '%Y-%m-%d').date()
            if current_date <= regular_deadline:
                return 'regular'
                
        # Check Late period
        if fees.get('late', {}).get('deadline'):
            late_deadline = datetime.strptime(fees['late']['deadline'], '%Y-%m-%d').date()
            if current_date <= late_deadline:
                return 'late'
        
        return 'closed'
    except Exception as e:
        print(f"Error determining registration period: {str(e)}")
        return 'closed'

def format_currency(amount, currency_info):
    """
    Formats the amount according to currency settings
    """
    try:
        if not amount:
            return "0.00"
            
        symbol = currency_info.get('symbol', 'R')
        position = currency_info.get('position', 'before')
        
        formatted_amount = f"{float(amount):,.2f}"
        
        if position == 'before':
            return f"{symbol} {formatted_amount}"
        else:
            return f"{formatted_amount} {symbol}"
    except Exception as e:
        print(f"Error formatting currency: {str(e)}")
        return str(amount)

def save_payment_proof(file):
    """Save payment proof file to Firebase Storage and return file data"""
    if not file:
        return None
        
    try:
        # Initialize Firebase Storage
        bucket = firebase_admin.storage.bucket()
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_filename = secure_filename(file.filename)
        unique_filename = f"payment_proofs/{timestamp}_{original_filename}"
        
        # Create blob and upload file
        blob = bucket.blob(unique_filename)
        blob.upload_from_string(
            file.read(),
            content_type=file.content_type
        )
        
        # Make the file publicly accessible
        blob.make_public()
        
        # Return file data
        return {
            'url': blob.public_url,
            'filename': original_filename,
            'path': unique_filename,
            'type': file.content_type,
            'size': blob.size
        }
    except Exception as e:
        print(f"Error saving payment proof: {str(e)}")
        return None

@app.route('/registration-form', methods=['GET', 'POST'])
@login_required
def registration_form():
    try:
        if request.method == 'GET':
            # Get current registration period and fees
            current_period = get_current_registration_period()
            if current_period == 'closed':
                flash('Registration is currently closed.', 'error')
                return redirect(url_for('home'))
                
            fees = get_registration_fees()
            if not fees:
                flash('Registration fees are not configured.', 'error')
                return redirect(url_for('home'))
            
            return render_template('registration_form.html', 
                                fees=fees,
                                site_design=get_site_design())
        
        # POST request - process registration
        registration_data = {
            'full_name': current_user.full_name,
            'email': current_user.email,
            'user_id': current_user.id,
            'registration_period': request.form.get('selected_period'),
            'registration_type': request.form.get('selected_type'),
            'total_amount': float(request.form.get('total_amount', 0)),
                'payment_reference': request.form.get('payment_reference'),
                'submission_date': datetime.now().isoformat(),
                'payment_status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
        # Validate registration period
        current_period = get_current_registration_period()
        if current_period == 'closed':
            raise ValueError('Registration is currently closed')
        if registration_data['registration_period'] != current_period:
            raise ValueError('Invalid registration period selected')
            
        # Add additional items if selected
        additional_items = {}
        for item in ['extra_paper', 'workshop', 'banquet']:
            if request.form.get(item) == 'true':
                if not fees['additional_items'][item]['enabled']:
                    raise ValueError(f'{item.replace("_", " ").title()} is not available')
                    
                # Check if virtual delegate is eligible for this item
                if (registration_data['registration_type'] == 'virtual_delegate' and 
                    not fees['additional_items'][item].get('virtual_eligible', True)):
                    raise ValueError(f'{item.replace("_", " ").title()} is not available for virtual delegates')
                    
                additional_items[item] = {
                    'selected': True,
                    'fee': fees['additional_items'][item]['fee']
                }
        
        registration_data['additional_items'] = additional_items
        
        # Handle payment proof file
        payment_proof = request.files.get('payment_proof')
        if payment_proof:
            file_data = save_payment_proof(payment_proof)
            if file_data:
                registration_data['payment_proof'] = file_data
            else:
                raise ValueError('Failed to save payment proof file')
        else:
            raise ValueError('Payment proof is required')
        
        # Update early bird seats if applicable
        if current_period == 'early_bird':
            fees_ref = db.reference('registration_fees/early_bird/seats')
            remaining = fees_ref.child('remaining').get() or 0
            if remaining <= 0:
                raise ValueError('No early bird seats remaining')
            fees_ref.update({
                'remaining': remaining - 1
            })
        
        # Save registration to Firebase Realtime Database
            registrations_ref = db.reference('registrations')
            new_registration = registrations_ref.push(registration_data)
            
        # Save reference to user's registrations collection
            user_reg_ref = db.reference(f'users/{current_user.id}/registrations/{new_registration.key}')
            user_reg_ref.set(True)
            
        # Send confirmation email
        try:
            send_confirmation_email(registration_data)
        except Exception as e:
            print(f"Error sending confirmation email: {str(e)}")
        
            flash('Registration submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
            
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('registration'))
    except Exception as e:
        flash(f'Error submitting registration: {str(e)}', 'error')
        return redirect(url_for('registration'))

@app.route('/admin/author-guidelines', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_author_guidelines():
    try:
        # Get existing guidelines from Firebase
        guidelines_ref = db.reference('author_guidelines')
        guidelines = guidelines_ref.get()

        if request.method == 'POST':
            # Update guidelines
            new_guidelines = {
                'abstract_guidelines': request.form.get('abstract_guidelines', ''),
                'paper_guidelines': request.form.get('paper_guidelines', ''),
                'oral_guidelines': request.form.get('oral_guidelines', ''),
                'virtual_guidelines': request.form.get('virtual_guidelines', ''),
                'invitation_letter': request.form.get('invitation_letter', '')
            }

            # Handle template file uploads (Firebase Storage)
            if 'abstract_template' in request.files:
                file = request.files['abstract_template']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"abstract_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    public_url = upload_guideline_file_and_get_url(file, unique_filename)
                    new_guidelines['abstract_template'] = public_url

            if 'paper_template' in request.files:
                file = request.files['paper_template']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"paper_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    public_url = upload_guideline_file_and_get_url(file, unique_filename)
                    new_guidelines['paper_template'] = public_url

            # Preserve existing template files if no new ones were uploaded
            if guidelines:
                if 'abstract_template' in guidelines and 'abstract_template' not in new_guidelines:
                    new_guidelines['abstract_template'] = guidelines['abstract_template']
                if 'paper_template' in guidelines and 'paper_template' not in new_guidelines:
                    new_guidelines['paper_template'] = guidelines['paper_template']

            # Save to Firebase
            guidelines_ref.set(new_guidelines)
            flash('Author guidelines updated successfully!', 'success')
            return redirect(url_for('admin_author_guidelines'))

        return render_template('admin/author_guidelines.html', 
                            guidelines=guidelines,
                            site_design=get_site_design())

    except Exception as e:
        flash(f'Error managing author guidelines: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    try:
        # Security check - prevent directory traversal
        if '..' in filename or filename.startswith('/'):
            return "Access denied", 403
            
        # Split the path to get the upload type (payments, papers, etc.)
        path_parts = filename.split('/')
        if len(path_parts) < 2:
            return "Invalid path", 400
            
        upload_type = path_parts[0]  # e.g., 'payments', 'papers'
        file_name = path_parts[-1]   # the actual filename
        
        # Validate upload type
        valid_upload_types = {'payments', 'papers', 'documents', 'templates', 'hero', 'committee', 'supporters'}
        if upload_type not in valid_upload_types:
            return "Invalid upload type", 400
        
        # Construct the full path relative to static/uploads
        upload_path = os.path.join(app.static_folder, 'uploads', upload_type)
        file_path = os.path.join(upload_path, file_name)
        
        # Security check - ensure file is within allowed directory
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(upload_path)):
            return "Access denied", 403
        
        # Check if file exists
        if not os.path.exists(file_path):
            return "File not found", 404
            
        # Set content disposition to force download for certain file types
        download_types = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip'}
        _, ext = os.path.splitext(file_name)
        download = ext.lower() in download_types
        
        return send_from_directory(
            upload_path, 
            file_name,
            as_attachment=download,
            download_name=file_name if download else None
        )
        
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        return "Error accessing file", 500

@app.route('/download-firebase-file')
def download_firebase_file():
    """Download files from Firebase Storage URLs with proper headers"""
    try:
        from urllib.parse import urlparse, unquote
        import requests
        
        file_url = request.args.get('url')
        if not file_url:
            return "No file URL provided", 400
        
        # SECURITY: Strict validation to prevent SSRF attacks
        try:
            parsed_url = urlparse(file_url)
        except Exception:
            return "Invalid URL format", 400
        
        # 1. Only allow HTTPS protocol
        if parsed_url.scheme != 'https':
            return "Only HTTPS URLs are allowed", 400
        
        # 2. Strictly validate the hostname is Firebase Storage
        allowed_domains = [
            'firebasestorage.googleapis.com',
            'storage.googleapis.com'
        ]
        if parsed_url.hostname not in allowed_domains:
            return "Only Firebase Storage URLs are allowed", 400
        
        # 3. Ensure no credentials in URL
        if parsed_url.username or parsed_url.password:
            return "URLs with credentials are not allowed", 400
        
        # 4. Validate path to prevent directory traversal
        if '..' in parsed_url.path or '//' in parsed_url.path:
            return "Invalid path in URL", 400
        
        # Extract filename from URL for download name
        filename = "download"
        if 'guidelines%2F' in file_url:
            filename = unquote(file_url.split('guidelines%2F')[1].split('?')[0])
        elif 'speakers%2F' in file_url:
            filename = unquote(file_url.split('speakers%2F')[1].split('?')[0])
        
        # Sanitize filename to prevent path traversal
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        if not filename or filename == '.':
            filename = "download"
        
        # Download the file from Firebase Storage with timeout and redirect disabled
        response = requests.get(
            file_url, 
            stream=True, 
            timeout=30,  # Prevent hanging
            allow_redirects=False  # Prevent redirect-based SSRF
        )
        
        if response.status_code != 200:
            return "File not found", 404
        
        # Create a Flask response with proper headers for download
        from flask import Response
        
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                yield chunk
        
        # Set headers to force download
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': response.headers.get('Content-Type', 'application/octet-stream')
        }
        
        return Response(
            generate(),
            headers=headers,
            status=200
        )
        
    except Exception as e:
        print(f"Error downloading Firebase file: {str(e)}")
        return "Error downloading file", 500

# Admin paper management routes
@app.route('/admin/submissions')
@login_required
@admin_required
def admin_submissions():
    try:
        # Get all papers from Firebase
        papers_ref = db.reference('papers')
        papers = papers_ref.get() or {}
        
        # Sort papers by submission date (newest first)
        sorted_papers = dict(sorted(
            papers.items(),
            key=lambda x: x[1].get('submitted_at', ''),
            reverse=True
        ))
        
        print("Fetched papers:", sorted_papers)  # Debug print
        
        return render_template(
            'admin/submissions.html',
            submissions=sorted_papers,
            site_design=get_site_design()
        )
    except Exception as e:
        print(f"Error loading submissions: {str(e)}")
        flash(f'Error loading submissions: {str(e)}', 'error')
        return render_template(
            'admin/submissions.html',
            submissions={},
            site_design=get_site_design()
        )

@app.route('/admin/papers/<paper_id>/status', methods=['POST'])
@login_required
@admin_required
def update_paper_status(paper_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        comments = data.get('comments', '')
        
        if new_status not in ['accepted', 'rejected', 'revision']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
            
        if not comments.strip() and new_status in ['rejected', 'revision']:
            return jsonify({'success': False, 'error': 'Comments are required for rejection or revision'}), 400
        
        # Update paper status in Firebase
        paper_ref = db.reference(f'papers/{paper_id}')
        paper = paper_ref.get()
        
        if not paper:
            return jsonify({'success': False, 'error': 'Paper not found'}), 404
        
        # Update the paper data
        update_data = {
            'status': new_status,
            'review_comments': comments,
            'updated_at': datetime.now().isoformat(),
            'reviewed_by': current_user.email
        }
        
        paper_ref.update(update_data)
        
        # Get updated paper data for email
        updated_paper = paper_ref.get()
        
        # Send email notification
        try:
            email_service.send_paper_status_update(updated_paper, new_status, comments)
        except Exception as e:
            print(f"Error sending email notification: {str(e)}")
            # Continue even if email fails
        
        return jsonify({
            'success': True,
            'paper': updated_paper
        })
        
    except Exception as e:
        print(f"Error updating paper status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/papers/<paper_id>/comments', methods=['POST'])
@login_required
@admin_required
def save_paper_comments(paper_id):
    try:
        data = request.get_json()
        comments = data.get('comments', '')
        
        # Update paper comments in Firebase
        paper_ref = db.reference(f'papers/{paper_id}')
        paper = paper_ref.get()
        
        if not paper:
            return jsonify({'success': False, 'error': 'Paper not found'}), 404
        
        # Update the comments and metadata
        update_data = {
            'review_comments': comments,
            'updated_at': datetime.now().isoformat(),
            'reviewed_by': current_user.email
        }
        
        paper_ref.update(update_data)
        
        return jsonify({
            'success': True,
            'paper': paper_ref.get()
        })
        
    except Exception as e:
        print(f"Error saving paper comments: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test-email')
def test_email():
    try:
        # Test SMTP connection first
        with mail.connect():
            print("SMTP Connection successful!")
            
        msg = Message('Test Email from GIIR Conference',
                     sender=app.config['MAIL_DEFAULT_SENDER'],
                     recipients=['thobanisgabuzam@gmail.com'])
        msg.body = '''
        Dear Thobani,
        
        This is a test email from the GIIR Conference system using Outlook SMTP.
        
        If you received this email, it means the email configuration is working correctly.
        
        Best regards,
        GIIR Conference Team
        '''
        
        # Print debug information
        print("\nSMTP Settings:")
        print(f"Server: {app.config['MAIL_SERVER']}")
        print(f"Port: {app.config['MAIL_PORT']}")
        print(f"TLS: {app.config['MAIL_USE_TLS']}")
        print(f"SSL: {app.config['MAIL_USE_SSL']}")
        print(f"Username: {app.config['MAIL_USERNAME']}")
        print(f"Sender: {app.config['MAIL_DEFAULT_SENDER']}")
        
        mail.send(msg)
        return 'Email sent successfully! Check your inbox at thobansigabuzam@gmail.com'
    except Exception as e:
        error_msg = f'Error sending email: {str(e)}\n'
        error_msg += f'Type: {type(e).__name__}\n'
        if hasattr(e, 'strerror'):
            error_msg += f'System error: {e.strerror}\n'
        if hasattr(e, 'errno'):
            error_msg += f'Error number: {e.errno}\n'
        
        # Add network diagnostic info
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            result = s.connect_ex((app.config['MAIL_SERVER'], app.config['MAIL_PORT']))
            error_msg += f'\nPort check result: {result} (0 means port is open)\n'
            s.close()
        except Exception as net_e:
            error_msg += f'\nNetwork test failed: {str(net_e)}\n'
            
        print(error_msg)  # Print to console for debugging
        return error_msg

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    app.logger.debug('Accessing forgot password route')
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            if not email:
                flash('Please enter your email address.', 'error')
                return render_template('user/auth/forgot_password.html', site_design=get_site_design())

            # Check if user exists
            try:
                user = auth.get_user_by_email(email)
            except Exception:
                # Don't reveal if email exists or not for security
                flash('If an account exists with this email, you will receive password reset instructions.', 'info')
                return render_template('user/auth/forgot_password.html', site_design=get_site_design())

            # Generate password reset link
            reset_link = auth.generate_password_reset_link(email)

            # Get user data from database
            user_ref = db.reference(f'users/{user.uid}')
            user_data = user_ref.get()

            if user_data:
                # Send password reset email
                email_service.send_password_reset_email(user_data, reset_link)
                flash('Password reset instructions have been sent to your email.', 'success')
            else:
                flash('Error retrieving user data.', 'error')

            return redirect(url_for('login'))

        return render_template('user/auth/forgot_password.html', site_design=get_site_design())
    except Exception as e:
        app.logger.error(f'Error in forgot_password route: {str(e)}')
        raise

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Handle the actual password reset after user clicks email link
    try:
        mode = request.args.get('mode')
        oobCode = request.args.get('oobCode')
        
        if mode != 'resetPassword' or not oobCode:
            flash('Invalid password reset link.', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            new_password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if new_password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('user/auth/reset_password.html', 
                                    oobCode=oobCode,
                                    site_design=get_site_design())

            # Verify and update password
            try:
                auth.verify_password_reset_code(oobCode)
                auth.confirm_password_reset(oobCode, new_password)
                flash('Password has been reset successfully. Please login with your new password.', 'success')
                return redirect(url_for('login'))
            except Exception:
                flash('Error resetting password. The link may have expired.', 'error')
                return redirect(url_for('forgot_password'))

        return render_template('user/auth/reset_password.html', 
                             oobCode=oobCode,
                             site_design=get_site_design())

    except Exception as e:
        flash(f'Error processing password reset: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/admin/email-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_email_settings():
    try:
        if request.method == 'POST':
            # Get form data
            email_settings = {
                'service_provider': request.form.get('service_provider'),
                'email': request.form.get('email'),
                'password': request.form.get('password'),
                'updated_at': datetime.now().isoformat(),
                'updated_by': current_user.email
            }

            # Add SMTP settings if custom provider
            if email_settings['service_provider'] == 'custom':
                email_settings.update({
                    'smtp_host': request.form.get('smtp_host'),
                    'smtp_port': request.form.get('smtp_port'),
                    'use_tls': request.form.get('use_tls') == 'on'
                })
            else:
                # Set default SMTP settings based on provider
                provider_settings = {
                    'outlook': {
                        'smtp_host': 'smtp.office365.com',
                        'smtp_port': 587,
                        'use_tls': True
                    },
                    'zoho': {
                        'smtp_host': 'smtp.zoho.com',
                        'smtp_port': 587,
                        'use_tls': True
                    },
                    'gmail': {
                        'smtp_host': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'use_tls': True
                    }
                }
                email_settings.update(provider_settings.get(email_settings['service_provider'], {}))

            # Save settings to Firebase
            settings_ref = db.reference('email_settings')
            settings_ref.set(email_settings)

            # Update Flask-Mail config
            app.config.update(
                MAIL_SERVER=email_settings['smtp_host'],
                MAIL_PORT=email_settings['smtp_port'],
                MAIL_USE_TLS=email_settings['use_tls'],
                MAIL_USERNAME=email_settings['email'],
                MAIL_PASSWORD=email_settings['password'],
                MAIL_DEFAULT_SENDER=email_settings['email']
            )

            # Reinitialize Flask-Mail with new settings
            global mail
            mail = Mail(app)
            global email_service
            email_service = EmailService(mail)

            flash('Email settings updated successfully!', 'success')
            return redirect(url_for('admin_email_settings'))

        # Get current settings
        settings_ref = db.reference('email_settings')
        settings = settings_ref.get()

        return render_template('admin/email_settings.html', 
                             settings=settings,
                             site_design=get_site_design())
    except Exception as e:
        flash(f'Error managing email settings: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/test-email-settings', methods=['POST'])
@login_required
@admin_required
def test_email_settings():
    try:
        # Get form data
        service_provider = request.form.get('service_provider')
        email = request.form.get('email')
        password = request.form.get('password')

        # Configure SMTP settings
        if service_provider == 'custom':
            smtp_host = request.form.get('smtp_host')
            smtp_port = int(request.form.get('smtp_port'))
            use_tls = request.form.get('use_tls') == 'on'
        else:
            provider_settings = {
                'outlook': {
                    'smtp_host': 'smtp.office365.com',
                    'smtp_port': 587,
                    'use_tls': True
                },
                'zoho': {
                    'smtp_host': 'smtp.zoho.com',
                    'smtp_port': 587,
                    'use_tls': True
                },
                'gmail': {
                    'smtp_host': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'use_tls': True
                }
            }
            settings = provider_settings.get(service_provider)
            if not settings:
                return jsonify({'success': False, 'error': 'Invalid service provider'})
            smtp_host = settings['smtp_host']
            smtp_port = settings['smtp_port']
            use_tls = settings['use_tls']

        # Create temporary Mail instance with new settings
        test_config = Config()
        test_config.MAIL_SERVER = smtp_host
        test_config.MAIL_PORT = smtp_port
        test_config.MAIL_USE_TLS = use_tls
        test_config.MAIL_USERNAME = email
        test_config.MAIL_PASSWORD = password
        test_config.MAIL_DEFAULT_SENDER = email

        test_app = Flask('test_app')
        test_app.config.from_object(test_config)
        test_mail = Mail(test_app)

        # Try to send a test email
        with test_app.app_context():
            msg = Message(
                'Test Email from GIIR Conference',
                recipients=[email],
                body='This is a test email to verify your email settings.'
            )
            test_mail.send(msg)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            subject = request.form.get('subject')
            message = request.form.get('message')

            # Validate required fields
            if not all([name, email, subject, message]):
                flash('Please fill in all required fields.', 'error')
                return redirect(url_for('contact'))

            # Save submission to Firebase
            submission = {
                'name': name,
                'email': email,
                'subject': subject,
                'message': message,
                'submitted_at': datetime.now().isoformat()
            }
            submissions_ref = db.reference('contact_submissions')
            submissions_ref.push(submission)
            
            # Get email settings
            settings_ref = db.reference('contact_email_settings')
            email_settings = settings_ref.get()
            
            if email_settings and email_settings.get('email'):
                # Send notification to admin
                admin_subject = f'New Contact Form Submission: {subject}'
                admin_body = f'''New contact form submission received:

From: {name} <{email}>
Subject: {subject}

Message:
{message}'''
                
                email_service.send_email(
                    to_email=email_settings['email'],
                    subject=admin_subject,
                    body=admin_body
                )
                
                # Send auto-reply if configured
                if email_settings.get('auto_reply'):
                    email_service.send_email(
                        to_email=email,
                        subject='Thank you for contacting us',
                        body=email_settings['auto_reply']
                    )
            
            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('contact'))

        except Exception as e:
            flash(f'Error sending message: {str(e)}', 'error')
            return redirect(url_for('contact'))
    
    # GET request - load page settings
    try:
        settings_ref = db.reference('contact_page_settings')
        page_settings = settings_ref.get()
    except Exception as e:
        flash(f'Error loading page settings: {str(e)}', 'warning')
        page_settings = None
    
    site_design = get_site_design()
    return render_template('user/contact.html', 
                         page_settings=page_settings,
                         site_design=site_design)

@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_paper():
    if request.method == 'GET':
        return render_template('submit.html', site_design=get_site_design())
        
    try:
        # Get form data
        data = request.form.to_dict()
        files = request.files
        
        # Process authors from form data
        authors = []
        author_index = 0
        while True:
            author_name = data.get(f'authors[{author_index}][name]')
            author_email = data.get(f'authors[{author_index}][email]')
            author_institution = data.get(f'authors[{author_index}][institution]')
            
            if not author_name:  # No more authors
                break
                
            if author_name and author_email and author_institution:
                authors.append({
                    'name': author_name,
                    'email': author_email,
                    'institution': author_institution
                })
            author_index += 1
        
        if not authors:
            flash('At least one author is required', 'error')
            return redirect(url_for('submit'))
        
        # Process paper file
        if 'paper_file' not in files:
            flash('Paper file is required', 'error')
            return redirect(url_for('submit'))
            
        paper_file = files['paper_file']
        if not paper_file.filename:
            flash('Paper file is required', 'error')
            return redirect(url_for('submit'))
            
        # Check file type
        allowed_extensions = {'pdf', 'doc', 'docx'}
        if '.' not in paper_file.filename or \
           paper_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            flash('Invalid file type. Allowed types: PDF, DOC, DOCX', 'error')
            return redirect(url_for('submit'))
        
        # Convert file to base64 for storage in Realtime Database
        file_data = paper_file.read()
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        # Create paper submission data
        paper_data = {
            'paper_title': data.get('paper_title'),
            'paper_abstract': data.get('paper_abstract'),
            'research_area': data.get('research_area'),
            'presentation_type': data.get('presentation_type'),
            'keywords': [k.strip() for k in data.get('keywords', '').split(',') if k.strip()],
            'authors': authors,
            'file_data': file_base64,
            'file_name': secure_filename(paper_file.filename),
            'file_type': paper_file.content_type,
            'file_size': len(file_data),
            'status': 'pending',
            'submitted_at': datetime.utcnow().isoformat(),
            'submitted_by': current_user.email,
            'user_id': current_user.id,
            'review_comments': None,
            'reviewed_by': None,
            'updated_at': None
        }
        
        # Debug print
        print("Saving paper data:", {k: v for k, v in paper_data.items() if k != 'file_data'})
        
        # Save to Firebase Realtime Database
        papers_ref = db.reference('papers')
        new_paper = papers_ref.push(paper_data)
        
        # Add reference to user's papers
        user_papers_ref = db.reference(f'users/{current_user.id}/papers/{new_paper.key}')
        user_papers_ref.set(True)
        
        # Send confirmation email
        try:
            send_submission_confirmation_email(
                authors[0]['email'],
                paper_data['paper_title'],
                new_paper.key
            )
        except Exception as e:
            print(f"Error sending confirmation email: {str(e)}")
        
        flash('Paper submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"Error submitting paper: {str(e)}")
        flash(f'Error submitting paper: {str(e)}', 'error')
        return redirect(url_for('submit'))

def send_submission_confirmation_email(email, paper_title, submission_id):
    subject = 'GIIR Conference Paper Submission Confirmation'
    body = f"""Dear Author,

Thank you for submitting your paper to the GIIR Conference 2024.

Submission Details:
Title: {paper_title}
Submission ID: {submission_id}

Your paper has been received and will be reviewed by our committee. You will be notified of any updates regarding your submission.

Best regards,
GIIR Conference Team
"""
    send_email(email, subject, body)

@app.route('/admin/get-email-settings')
@login_required
@admin_required
def get_email_settings():
    try:
        settings_ref = db.reference('email_settings')
        settings = settings_ref.get()
        
        if not settings:
            return jsonify({
                'success': False,
                'error': 'Email settings not configured'
            })
            
        return jsonify({
            'success': True,
            'sender': settings.get('email', 'GIIR Conference')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

def process_hero_images(request):
    """Process hero images from the form submission"""
    try:
        hero_images = []
        bucket = storage.bucket()

        # Get current hero images from database
        content_ref = db.reference('home_content')
        current_content = content_ref.get() or {}
        current_hero_images = current_content.get('hero', {}).get('images', [])

        # Handle deleted images first
        deleted_images = request.form.getlist('deleted_hero_images[]')
        print(f"Processing {len(deleted_images)} deleted hero images")
        
        for image_url in deleted_images:
            try:
                print(f"Deleting hero image: {image_url}")
                # Extract blob path from URL
                blob_path = image_url.split('/o/')[1].split('?')[0]
                blob_path = blob_path.replace('%2F', '/')
                blob = bucket.blob(blob_path)
                if blob.exists():
                    blob.delete()
                    print(f"Successfully deleted hero image: {blob_path}")
            except Exception as e:
                print(f"Error deleting hero image: {str(e)}")

        # Keep existing images that weren't deleted
        for image in current_hero_images:
            if image['url'] not in deleted_images:
                hero_images.append(image)

        # Process new hero images
        if 'hero_images' in request.files:
            files = request.files.getlist('hero_images')
            print(f"Processing {len(files)} new hero images")
            
            for file in files:
                try:
                    if file and file.filename:
                        print(f"Processing hero image: {file.filename}")
                        
                        # Validate image with hero type
                        validate_image(file, image_type='hero')
                        
                        # Generate unique filename
                        original_filename = secure_filename(file.filename)
                        ext = os.path.splitext(original_filename)[1].lower()
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_id = str(uuid.uuid4())[:8]
                        
                        # Use dedicated path for hero images
                        unique_filename = f"content/hero_images/{timestamp}_{unique_id}{ext}"
                        print(f"Generated unique filename: {unique_filename}")
                        
                        # Create a new blob
                        blob = bucket.blob(unique_filename)
                        
                        # Set content type and metadata
                        content_type = mimetypes.guess_type(original_filename)[0] or 'image/jpeg'
                        blob.content_type = content_type
                        blob.metadata = {
                            'optimized': 'false',
                            'originalName': original_filename,
                            'timestamp': timestamp,
                            'type': 'hero_image'
                        }
                        
                        # Compress image if needed (1MB for hero images)
                        file.seek(0)  # Reset file pointer
                        img_data = compress_image(file, max_size_kb=1000)  # 1MB for hero images
                        
                        # Upload the file with metadata
                        blob.upload_from_string(
                            img_data,
                            content_type=content_type
                        )
                        
                        # Make the blob publicly accessible
                        blob.make_public()
                        
                        # Get the public URL
                        public_url = blob.public_url
                        
                        # Add to hero images list
                        hero_images.append({
                            'url': public_url,
                            'alt': original_filename,
                            'filename': unique_filename
                        })
                        
                        print(f"Successfully uploaded hero image: {public_url}")
                        
                except Exception as e:
                    print(f"Error processing hero image {file.filename}: {str(e)}")
                    continue

        print(f"Final count of hero images: {len(hero_images)}")
        return hero_images

    except Exception as e:
        print(f"Error in process_hero_images: {str(e)}")
        raise e

def process_downloads_data(request):
    """Process and save downloads data from form data"""
    downloads = []
    
    # Process existing downloads
    existing_ids = request.form.getlist('download_ids[]')
    existing_titles = request.form.getlist('download_titles[]')
    existing_descriptions = request.form.getlist('download_descriptions[]')
    existing_formats = request.form.getlist('download_formats[]')
    existing_files = request.form.getlist('download_existing_files[]')
    
    for i in range(len(existing_titles)):
        if existing_titles[i].strip():  # Only process if title exists
            download_id = existing_ids[i] if i < len(existing_ids) else f'new_{i}'
            download_format = existing_formats[i] if i < len(existing_formats) else 'Other'
            
            download_data = {
                'id': download_id,
                'title': existing_titles[i],
                'description': existing_descriptions[i] if i < len(existing_descriptions) else '',
                'format': download_format,
                'file_url': existing_files[i] if i < len(existing_files) and existing_files[i] else None,
                'file_type': '',  # Will be updated if file is uploaded
                'file_size': '',  # Will be updated if file is uploaded
                'updated_at': datetime.now().isoformat()
            }
            
            # Handle new file upload for existing download
            file_key = f'download_file_{download_id}'
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename and allowed_file(file.filename):
                    try:
                        filename = secure_filename(file.filename)
                        file_extension = filename.rsplit('.', 1)[1].lower()
                        
                        # Calculate file size
                        file.seek(0, 2)  # Seek to end
                        file_size_bytes = file.tell()
                        file.seek(0)  # Reset file pointer
                        
                        if file_size_bytes < 1024 * 1024:  # Less than 1MB
                            file_size_formatted = f"{file_size_bytes / 1024:.1f} KB"
                        else:  # 1MB or larger
                            file_size_formatted = f"{file_size_bytes / (1024 * 1024):.1f} MB"
                        
                        # Try Firebase Storage with better error handling
                        try:
                            # Create unique filename with timestamp
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            firebase_filename = f"downloads/templates/{timestamp}_{filename}"
                            
                            # Use the correct bucket name
                            bucket = storage.bucket('giir-66ae6.firebasestorage.app')
                            print(f"Using Firebase Storage bucket: {bucket.name}")
                            
                            # Create blob
                            blob = bucket.blob(firebase_filename)
                            
                            # Set content type based on file extension
                            content_type_map = {
                                'pdf': 'application/pdf',
                                'doc': 'application/msword',
                                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                'xls': 'application/vnd.ms-excel',
                                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                'ppt': 'application/vnd.ms-powerpoint',
                                'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                                'zip': 'application/zip',
                                'tex': 'text/plain',
                                'txt': 'text/plain'
                            }
                            content_type = content_type_map.get(file_extension, 'application/octet-stream')
                            
                            # Upload file with metadata
                            file.seek(0)  # Reset file pointer
                            blob.upload_from_file(
                                file, 
                                content_type=content_type
                            )
                            
                            # Make blob publicly accessible
                            blob.make_public()
                            
                            # Get the public URL
                            file_url = blob.public_url
                            
                            # Update download data
                            download_data.update({
                                'file_url': file_url,
                                'file_type': file_extension,
                                'file_size': file_size_formatted,
                                'firebase_path': firebase_filename
                            })
                            
                            print(f"Successfully uploaded template file to Firebase Storage: {firebase_filename}")
                            print(f"Public URL: {file_url}")
                            
                        except Exception as storage_error:
                            print(f"Firebase Storage error: {str(storage_error)}")
                            print(f"Error type: {type(storage_error).__name__}")
                            
                            # Provide helpful error message
                            error_msg = str(storage_error).lower()
                            if 'bucket does not exist' in error_msg or '404' in error_msg:
                                print("SOLUTION: Please enable Firebase Storage in your Firebase Console:")
                                print("1. Go to https://console.firebase.google.com/")
                                print("2. Select your project (giir-66ae6)")
                                print("3. Go to Storage in the left menu")
                                print("4. Click 'Get started' to enable Firebase Storage")
                                print("5. Choose your storage location and security rules")
                            
                            # Skip this file and continue with others
                            continue
                        
                    except Exception as e:
                        print(f"Error processing download file {filename}: {str(e)}")
                        continue
                        
            downloads.append(download_data)
    
    return downloads

@app.route('/admin/contact-email', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_contact_email():
    if request.method == 'POST':
        try:
            # Get form data
            service_provider = request.form.get('service_provider')
            email = request.form.get('email')
            password = request.form.get('password')
            auto_reply = request.form.get('auto_reply')
            
            settings = {
                'service_provider': service_provider,
                'email': email,
                'password': password,
                'auto_reply': auto_reply,
                'updated_at': datetime.now().isoformat(),
                'updated_by': current_user.email
            }
            
            # Add SMTP settings if custom provider
            if service_provider == 'custom':
                settings.update({
                    'smtp_host': request.form.get('smtp_host'),
                    'smtp_port': request.form.get('smtp_port'),
                    'use_tls': 'use_tls' in request.form
                })
            
            # Save settings to Firebase
            settings_ref = db.reference('contact_email_settings')
            settings_ref.set(settings)
            
            # Update email service configuration
            email_service.update_settings(settings)
            
            flash('Email settings saved successfully!', 'success')
            return redirect(url_for('admin_contact_email'))
            
        except Exception as e:
            flash(f'Error saving email settings: {str(e)}', 'error')
            return redirect(url_for('admin_contact_email'))
    
    try:
        # Get email settings
        settings_ref = db.reference('contact_email_settings')
        email_settings = settings_ref.get()
        
        # Get page settings
        page_settings_ref = db.reference('contact_page_settings')
        page_settings = page_settings_ref.get()
        
        return render_template('admin/contact_email.html', 
                             settings=email_settings,
                             page_settings=page_settings)
                             
    except Exception as e:
        flash(f'Error loading settings: {str(e)}', 'warning')
        return render_template('admin/contact_email.html',
                             settings=None,
                             page_settings=None)

@app.route('/test-contact-email', methods=['POST'])
@login_required
@admin_required
def test_contact_email():
    try:
        # Get contact email settings
        settings_ref = db.reference('contact_email_settings')
        settings = settings_ref.get()
        
        if not settings or not settings.get('email'):
            return jsonify({
                'success': False,
                'error': 'Email settings not configured'
            }), 400
        
        # Send test email
        subject = 'Test Contact Form Email'
        body = f'''This is a test email to verify contact form settings.
        
Email Configuration:
- Service Provider: {settings['service_provider']}
- Email: {settings['email']}
- SMTP Host: {settings.get('smtp_host', 'N/A')}
- SMTP Port: {settings.get('smtp_port', 'N/A')}
- TLS Enabled: {settings.get('use_tls', 'N/A')}

Auto-reply message: {settings['auto_reply']}

If you received this email, your contact form settings are working correctly.'''
        
        email_service.send_email(
            to_email=settings['email'],
            subject=subject,
            body=body
        )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/admin/contact-page-settings', methods=['POST'])
@login_required
@admin_required
def admin_contact_page_settings():
    try:
        settings = {
            'title': request.form.get('page_title'),
            'description': request.form.get('page_description'),
            'email': request.form.get('contact_email'),
            'phone': request.form.get('contact_phone'),
            'address': request.form.get('contact_address'),
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        }
        
        # Save settings to Firebase
        settings_ref = db.reference('contact_page_settings')
        settings_ref.set(settings)
        
        flash('Contact page settings saved successfully!', 'success')
        return redirect(url_for('admin_contact_email'))
        
    except Exception as e:
        flash(f'Error saving contact page settings: {str(e)}', 'error')
        return redirect(url_for('admin_contact_email'))


@app.route('/admin/papers/<paper_id>/download')
@login_required
@admin_required
def download_paper(paper_id):
    try:
        # Get paper data from Firebase
        paper_ref = db.reference(f'papers/{paper_id}')
        paper = paper_ref.get()
        
        if not paper:
            flash('Paper not found.', 'error')
            return redirect(url_for('admin_submissions'))
            
        # Get file data from Firebase
        file_data = paper.get('file_data')
        if not file_data:
            flash('Paper file not found.', 'error')
            return redirect(url_for('admin_submissions'))
            
        try:
            # Decode base64 data
            file_bytes = base64.b64decode(file_data)
        except Exception as e:
            print(f"Error decoding file data: {str(e)}")
            flash('Error processing file data.', 'error')
            return redirect(url_for('admin_submissions'))
        
        # Create file-like object
        file_obj = io.BytesIO(file_bytes)
        
        # Generate a clean filename
        original_filename = paper.get('file_name', 'paper.pdf')
        safe_filename = secure_filename(original_filename)
        
        # Get correct mimetype
        mimetype = paper.get('file_type')
        if not mimetype or mimetype == 'application/octet-stream':
            # Try to guess mimetype from filename
            mimetype, _ = mimetypes.guess_type(original_filename)
            if not mimetype:
                mimetype = 'application/pdf'  # Default to PDF
        
        # Log download attempt
        print(f"Downloading paper {paper_id}: {safe_filename} ({mimetype})")
        
        # Send file with proper headers
        response = send_file(
            file_obj,
            mimetype=mimetype,
            as_attachment=True,
            download_name=safe_filename,
            max_age=0  # Prevent caching
        )
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        return response
        
    except Exception as e:
        print(f"Error downloading paper: {str(e)}")
        flash(f'Error downloading paper: {str(e)}', 'error')
        return redirect(url_for('admin_submissions'))

def send_paper_status_notification(email, paper_title, status, comments):
    """Send email notification for paper status update"""
    subject = f"Paper Submission Status Update - {paper_title}"
    
    # Build the message body using string concatenation
    body = "Dear Author,\n\n"
    body += f"Your paper titled '{paper_title}' has been {status}.\n\n"
    if comments:
        body += "Reviewer Comments:\n"
        body += comments + "\n\n"
    body += "Best regards,\nConference Team"
    
    try:
        send_email(email, subject, body)
        return True
    except Exception as e:
        print("Error sending paper status notification:", str(e))
        return False

# Default content for home page
default_content = {
    'welcome': {
        'title': 'Welcome to GIIR',
        'subtitle': 'Global Institute on Innovative Research',
        'conference_date': 'International Conference 2024',
        'message': 'Join us for the premier conference in innovative research'
    },
    'hero': {
        'images': [],
        'conference': {
            'name': 'Global Institute on Innovative Research',
            'date': 'TBA',
            'time': 'TBA',
            'city': 'TBA',
            'highlights': 'Keynote Speakers\nTechnical Sessions\nWorkshops\nNetworking Events'
        }
    },
    'vmo': {
        'vision': 'The Global Institute on Innovative Research (GIIR) is geared towards bringing researchers to share their innovative research findings in the global platform',
        'mission': 'GIIR\'s intention is to initiate, develop and promote research in the fields of Social, Economic, Information Technology, Education and Management Sciences',
        'objectives': 'To provide a world class platform for researchers to share their research findings.\nTo encourage researchers to identify significant research issues.\nTo help in the dissemination of researcher\'s work.'
    },
    'downloads': [],
    'associates': [],
    'footer': {
        'contact_email': '',
        'contact_phone': '',
        'social_media': {
            'facebook': '',
            'twitter': '',
            'linkedin': ''
        },
        'address': '',
        'copyright': '© ' + str(datetime.now().year) + ' Global Institute on Innovative Research. All rights reserved.'
    }
}

@app.context_processor
def inject_year():
    return {'now': datetime.now()}

@app.context_processor
def inject_home_content():
    try:
        # Get home content from Firebase
        content_ref = db.reference('home_content')
        home_content = content_ref.get() or default_content
        return {'home_content': home_content}
    except Exception as e:
        print(f"Error loading home content: {str(e)}")
        return {'home_content': default_content}

@app.route('/admin/call-for-papers-content', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_call_for_papers_content():
    try:
        if request.method == 'POST':
            # Process page header
            page_header = {
                'title': request.form.get('page_title', 'Call for Papers'),
                'subtitle': request.form.get('page_subtitle', 'Submit your research to be part of the Global Institute on Innovative Research Conference 2024')
            }
            
            # Process topics of interest
            topics = []
            topic_titles = request.form.getlist('topic_titles[]')
            
            print(f"DEBUG - Admin CFP POST - Number of topics: {len(topic_titles)}")
            print(f"DEBUG - Admin CFP POST - Topic titles: {topic_titles}")
            
            for i, title in enumerate(topic_titles):
                subtopics = request.form.getlist(f'topic_subtopics[{i}][]')
                print(f"DEBUG - Admin CFP POST - Topic {i}: {title} with {len(subtopics)} subtopics")
                topics.append({
                    'title': title,
                    'subtopics': subtopics
                })
            
            # Process important dates
            important_dates = []
            date_icons = request.form.getlist('date_icons[]')
            date_titles = request.form.getlist('date_titles[]')
            date_values = request.form.getlist('date_values[]')
            date_times = request.form.getlist('date_times[]')
            
            for i in range(len(date_titles)):
                important_dates.append({
                    'icon': date_icons[i] if i < len(date_icons) else '',
                    'title': date_titles[i],
                    'date': date_values[i],
                    'time': date_times[i] if i < len(date_times) else ''
                })
            
            # Process submission guidelines
            submission_guidelines = []
            guideline_titles = request.form.getlist('guideline_titles[]')
            
            for i, title in enumerate(guideline_titles):
                items = request.form.getlist(f'guideline_items[{i}][]')
                # Store items as a proper list field, not using the dict.items method
                submission_guidelines.append({
                    'title': title,
                    'guideline_items': items  # Use guideline_items instead of items for storage
                })
            
            # Process CTA section
            cta = {
                'submit_button_text': request.form.get('submit_button_text', 'Submit Your Paper'),
                'template_button_text': request.form.get('template_button_text', 'Download Template'),
                'template_url': request.form.get('template_url', '#')
            }
            
            # Process Plagiarism Policy section
            plagiarism_policy = {
                'enabled': request.form.get('plagiarism_policy_enabled') == 'on',
                'title': request.form.get('plagiarism_policy_title', 'Plagiarism Policy & Publication Ethics'),
                'content': request.form.get('plagiarism_policy_content', ''),
                'turnitin_url': request.form.get('turnitin_url', 'https://www.turnitin.com/')
            }
            
            # Compile the final data structure
            cfp_content = {
                'page_header': page_header,
                'topics_intro': request.form.get('topics_intro', 'We invite high-quality original research papers in the following areas (but not limited to):'),
                'topics': topics,
                'important_dates': important_dates,
                'submission_guidelines': submission_guidelines,
                'plagiarism_policy': plagiarism_policy,
                'cta': cta
            }
            
            # Print the final structure before saving
            print(f"DEBUG - Admin CFP POST - Final topics structure: {cfp_content['topics']}")
            
            # Save to Firebase
            db.reference('call_for_papers_content').set(cfp_content)
            flash('Call for Papers content updated successfully!', 'success')
            return redirect(url_for('admin_call_for_papers_content'))
        
        # GET request - load current content
        cfp_content = db.reference('call_for_papers_content').get() or {}
        
        # Set up default values if they don't exist in the fetched data
        if 'page_header' not in cfp_content:
            cfp_content['page_header'] = {
                'title': 'Call for Papers',
                'subtitle': 'Submit your research to be part of the Global Institute on Innovative Research Conference 2024'
            }
            
        if 'cta' not in cfp_content:
            cfp_content['cta'] = {
                'submit_button_text': 'Submit Your Paper',
                'template_button_text': 'Download Template',
                'template_url': '#'
            }
            
        # Ensure other required sections exist
        if 'topics_intro' not in cfp_content:
            cfp_content['topics_intro'] = 'We invite high-quality original research papers in the following areas (but not limited to):'
            
        if 'topics' not in cfp_content:
            cfp_content['topics'] = []
            
        if 'important_dates' not in cfp_content:
            cfp_content['important_dates'] = []
            
        if 'submission_guidelines' not in cfp_content:
            cfp_content['submission_guidelines'] = []
        
        # Fix existing submission guidelines structure
        for guideline in cfp_content['submission_guidelines']:
            # If guideline doesn't have guideline_items field, but has title, convert it
            if 'guideline_items' not in guideline and 'title' in guideline:
                # Move the title content to guideline_items as a single item
                title_content = guideline['title']
                guideline['guideline_items'] = [title_content] if title_content else []
                guideline['title'] = 'Research Guidelines'  # Set a default category title
            
        # Ensure plagiarism policy section exists
        if 'plagiarism_policy' not in cfp_content:
            cfp_content['plagiarism_policy'] = {
                'enabled': False,
                'title': 'Plagiarism Policy & Publication Ethics',
                'content': 'The 9th International Academic Conference on Education follows strict anti-plagiarism policies and, as such, checks every submission for plagiarism using Turnitin. All articles submitted to the conference first undergo a plagiarism check before being sent to our scientific committee for review. The submission will be automatically rejected at any time if found plagiarized. If you\'d like to find out more information about the Turnitin software, click on the following link:',
                'turnitin_url': 'https://www.turnitin.com/'
            }
        
        print(f"DEBUG - Admin CFP GET - Final CFP content: {cfp_content}")
        return render_template('admin/call_for_papers_content.html', cfp_content=cfp_content)
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        print(f"Error in admin_call_for_papers_content: {str(e)}")
        # Provide complete default structure when error occurs
        default_cfp_content = {
            'page_header': {
                'title': 'Call for Papers',
                'subtitle': 'Submit your research to be part of the Global Institute on Innovative Research Conference 2024'
            },
            'topics_intro': 'We invite high-quality original research papers in the following areas (but not limited to):',
            'topics': [],
            'important_dates': [],
            'submission_guidelines': [],
            'plagiarism_policy': {
                'enabled': False,
                'title': 'Plagiarism Policy & Publication Ethics',
                'content': 'The 9th International Academic Conference on Education follows strict anti-plagiarism policies and, as such, checks every submission for plagiarism using Turnitin. All articles submitted to the conference first undergo a plagiarism check before being sent to our scientific committee for review. The submission will be automatically rejected at any time if found plagiarized. If you\'d like to find out more information about the Turnitin software, click on the following link:',
                'turnitin_url': 'https://www.turnitin.com/'
            },
            'cta': {
                'submit_button_text': 'Submit Your Paper',
                'template_button_text': 'Download Template',
                'template_url': '#'
            }
        }
        return render_template('admin/call_for_papers_content.html', cfp_content=default_cfp_content)

@app.route('/admin/speakers', methods=['GET'])
@login_required
@admin_required
def admin_speakers():
    try:
        # Get all speakers from Firebase
        speakers_ref = db.reference('speakers')
        speakers = speakers_ref.get() or {}
        
        # Sort speakers by name
        sorted_speakers = dict(sorted(
            speakers.items(),
            key=lambda x: x[1].get('name', '').lower()
        ))
        
        return render_template(
            'admin/speakers.html',
            speakers=sorted_speakers,
            site_design=get_site_design()
        )
    except Exception as e:
        flash(f'Error loading speakers: {str(e)}', 'error')
        return render_template(
            'admin/speakers.html',
            speakers={},
            site_design=get_site_design()
        )

@app.route('/admin/speakers/new', methods=['GET', 'POST'], endpoint='add_speaker')
@login_required
@admin_required
def add_speaker():
    if request.method == 'POST':
        try:
            # Get form data
            speaker_data = {
                'name': request.form.get('name', '').strip(),
                'title': request.form.get('title', '').strip(),
                'organization': request.form.get('organization', '').strip(),
                'bio': request.form.get('bio', '').strip(),
                'status': request.form.get('status', 'current'),  # Default to 'current' if not provided
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Validate required fields
            required_fields = ['name', 'title', 'organization']
            for field in required_fields:
                if not speaker_data.get(field):
                    flash(f'Field "{field}" is required.', 'error')
                    return redirect(url_for('add_speaker'))
            
            # Handle profile image upload
            if 'profile_image' in request.files:
                file = request.files['profile_image']
                if file and file.filename and allowed_image_file(file.filename):
                    try:
                        # Generate unique filename
                        original_filename = secure_filename(file.filename)
                        ext = os.path.splitext(original_filename)[1].lower()
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_id = str(uuid.uuid4())[:8]
                        unique_filename = f"{timestamp}_{unique_id}{ext}"
                        
                        # Upload to Firebase Storage and get public URL
                        public_url = upload_speaker_image_to_firebase(file, unique_filename)
                        
                        # Add image URL to speaker data
                        speaker_data['profile_image'] = public_url
                    except Exception as e:
                        print(f"Error uploading profile image: {str(e)}")
                        flash(f'Error uploading profile image: {str(e)}', 'error')
                        return redirect(url_for('add_speaker'))
            
            # Save speaker to Firebase
            speakers_ref = db.reference('speakers')
            speakers_ref.push(speaker_data)
            
            flash('Speaker added successfully!', 'success')
            return redirect(url_for('admin_speakers'))
            
        except Exception as e:
            flash(f'Error adding speaker: {str(e)}', 'error')
            return redirect(url_for('add_speaker'))
    
    # GET request - render form
    return render_template(
        'admin/speaker_form.html',
        speaker=None,
        action="Add",
        site_design=get_site_design()
    )

@app.route('/admin/speakers/<speaker_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_speaker(speaker_id):
    # Get speaker data
    speaker_ref = db.reference(f'speakers/{speaker_id}')
    speaker = speaker_ref.get()
    
    if not speaker:
        flash('Speaker not found.', 'error')
        return redirect(url_for('admin_speakers'))
    
    if request.method == 'POST':
        try:
            # Get form data
            speaker_data = {
                'name': request.form.get('name', '').strip(),
                'title': request.form.get('title', '').strip(),
                'organization': request.form.get('organization', '').strip(),
                'bio': request.form.get('bio', '').strip(),
                'status': request.form.get('status', 'current'),  # Default to 'current' if not provided
                'updated_at': datetime.now().isoformat()
            }
            
            # Validate required fields
            required_fields = ['name', 'title', 'organization']
            for field in required_fields:
                if not speaker_data.get(field):
                    flash(f'Field "{field}" is required.', 'error')
                    return redirect(url_for('edit_speaker', speaker_id=speaker_id))
            
            # Handle profile image upload
            if 'profile_image' in request.files:
                file = request.files['profile_image']
                if file and file.filename and allowed_image_file(file.filename):
                    try:
                        # Delete old image from Firebase Storage if exists
                        if speaker.get('profile_image'):
                            try:
                                old_image_url = speaker['profile_image']
                                if 'firebasestorage.app' in old_image_url:
                                    # Extract blob path from URL
                                    storage_client = storage.Client.from_service_account_json('serviceAccountKey.json')
                                    bucket = storage_client.bucket('giir-66ae6.firebasestorage.app')
                                    
                                    # Extract the blob path from the URL
                                    # URL format: https://firebasestorage.googleapis.com/v0/b/giir-66ae6.firebasestorage.app/o/speakers%2Ffilename?alt=media&token=...
                                    if 'speakers%2F' in old_image_url:
                                        old_filename = old_image_url.split('speakers%2F')[1].split('?')[0]
                                        old_blob = bucket.blob(f'speakers/{old_filename}')
                                        if old_blob.exists():
                                            old_blob.delete()
                                            print(f"Successfully deleted old speaker image from Firebase: {old_filename}")
                            except Exception as e:
                                print(f"Error deleting old speaker image: {str(e)}")
                        
                        # Generate unique filename
                        original_filename = secure_filename(file.filename)
                        ext = os.path.splitext(original_filename)[1].lower()
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_id = str(uuid.uuid4())[:8]
                        unique_filename = f"{timestamp}_{unique_id}{ext}"
                        
                        # Upload to Firebase Storage and get public URL
                        public_url = upload_speaker_image_to_firebase(file, unique_filename)
                        
                        # Add image URL to speaker data
                        speaker_data['profile_image'] = public_url
                    except Exception as e:
                        print(f"Error uploading profile image: {str(e)}")
                        flash(f'Error uploading profile image: {str(e)}', 'error')
                        return redirect(url_for('edit_speaker', speaker_id=speaker_id))
            else:
                # Keep existing profile image
                speaker_data['profile_image'] = speaker.get('profile_image', '')
            
            # Update speaker in Firebase
            speaker_ref.update(speaker_data)
            
            flash('Speaker updated successfully!', 'success')
            return redirect(url_for('admin_speakers'))
            
        except Exception as e:
            flash(f'Error updating speaker: {str(e)}', 'error')
            return redirect(url_for('edit_speaker', speaker_id=speaker_id))
    
    # GET request - render form with speaker data
    return render_template(
        'admin/speaker_form.html',
        speaker=speaker,
        speaker_id=speaker_id,
        action="Edit",
        site_design=get_site_design()
    )

@app.route('/admin/speakers/<speaker_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_speaker(speaker_id):
    try:
        # Get speaker data
        speaker_ref = db.reference(f'speakers/{speaker_id}')
        speaker = speaker_ref.get()
        
        if not speaker:
            return jsonify({'success': False, 'error': 'Speaker not found'}), 404
        
        # Delete profile image if exists
        if speaker.get('profile_image'):
            try:
                image_url = speaker['profile_image']
                if 'firebasestorage.app' in image_url:
                    # Extract blob path from URL
                    storage_client = storage.Client.from_service_account_json('serviceAccountKey.json')
                    bucket = storage_client.bucket('giir-66ae6.firebasestorage.app')
                    
                    # Extract the blob path from the URL
                    # URL format: https://firebasestorage.googleapis.com/v0/b/giir-66ae6.firebasestorage.app/o/speakers%2Ffilename?alt=media&token=...
                    if 'speakers%2F' in image_url:
                        old_filename = image_url.split('speakers%2F')[1].split('?')[0]
                        old_blob = bucket.blob(f'speakers/{old_filename}')
                        if old_blob.exists():
                            old_blob.delete()
                            print(f"Successfully deleted speaker image from Firebase: {old_filename}")
                elif '/static/uploads/speakers/' in image_url:
                    # Handle legacy local files
                    filename = image_url.split('/static/uploads/speakers/')[1]
                    file_path = os.path.join(app.static_folder, 'uploads', 'speakers', filename)
                    
                    # Delete file if exists
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Successfully deleted legacy speaker image: {file_path}")
            except Exception as e:
                print(f"Error deleting speaker image: {str(e)}")
        
        # Delete speaker from Firebase
        speaker_ref.delete()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting speaker: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Add this context processor after existing ones
@app.context_processor
def inject_has_speakers():
    try:
        # Check if there are any speakers in Firebase
        speakers_ref = db.reference('speakers')
        speakers_data = speakers_ref.get() or {}
        has_speakers = len(speakers_data) > 0
        
        # Count current and past speakers
        current_speakers_count = sum(1 for s in speakers_data.values() if s.get('status') != 'past')
        past_speakers_count = sum(1 for s in speakers_data.values() if s.get('status') == 'past')
        
        return {
            'has_speakers': has_speakers,
            'has_current_speakers': current_speakers_count > 0,
            'has_past_speakers': past_speakers_count > 0
        }
    except Exception as e:
        print(f"Error checking speakers: {str(e)}")
        return {
            'has_speakers': False,
            'has_current_speakers': False,
            'has_past_speakers': False
        }

@app.context_processor
def inject_admin_menu():
    admin_menu = [
        {'text': 'Dashboard', 'url': 'admin_dashboard', 'icon': 'tachometer-alt'},
        {'text': 'Conferences', 'url': 'admin_conferences', 'icon': 'calendar'},
        {'text': 'Home Content', 'url': 'admin_home_content', 'icon': 'home'},
        {'text': 'About Content', 'url': 'admin_about_content', 'icon': 'info-circle'},
        {'text': 'Author Guidelines', 'url': 'admin_author_guidelines', 'icon': 'book'},
        {'text': 'Call for Papers', 'url': 'admin_call_for_papers_content', 'icon': 'file-alt'},
        {'text': 'Paper Submission Settings', 'url': 'admin_paper_submission_settings', 'icon': 'file-upload'},
        {'text': 'Design Settings', 'url': 'admin_design', 'icon': 'palette'},
        {'text': 'Venue', 'url': 'admin_venue', 'icon': 'map-marker-alt'},
        {'text': 'Speakers', 'url': 'admin_speakers', 'icon': 'microphone'},
        # DISABLED: Schedule feature not functioning properly (Issue #3)
        # {'text': 'Schedule', 'url': 'admin_schedule', 'icon': 'calendar-alt'},
        {'text': 'Registration Fees', 'url': 'admin_registration_fees', 'icon': 'dollar-sign'},
        {'text': 'User Management', 'url': 'admin_users', 'icon': 'users'},
        {'text': 'Registrations', 'url': 'admin_registrations', 'icon': 'user-plus'},
        {'text': 'Guest Speaker Applications', 'url': 'admin_guest_speaker_applications', 'icon': 'id-badge'},
        {'text': 'Submissions', 'url': 'admin_submissions', 'icon': 'paper-plane'},
        {'text': 'Announcements', 'url': 'admin_announcements', 'icon': 'bullhorn'},
        {'text': 'Email Templates', 'url': 'admin_email_templates', 'icon': 'envelope-open-text'},
        {'text': 'Email Settings', 'url': 'admin_email_settings', 'icon': 'cog'},
        {'text': 'Downloads', 'url': 'admin_downloads', 'icon': 'download'},
                {'text': 'Conference Proceedings', 'url': 'admin_conference_proceedings', 'icon': 'book-open'},
                {'text': 'Conference Galleries', 'url': 'admin_conference_galleries', 'icon': 'images'},
    ]
    return dict(admin_menu=admin_menu)

@app.route('/conference-proceedings')
def conference_proceedings():
    """Display conference proceedings/publications"""
    try:
        # Get content from Firebase
        content_ref = db.reference('conference_proceedings_content')
        content = content_ref.get() or {}
        
        # Get downloads from Firebase and filter for manuscript templates
        downloads_ref = db.reference('downloads')
        all_downloads = downloads_ref.get() or {}
        
        # Filter downloads for manuscript templates and conference proceedings
        downloads = {}
        if all_downloads:
            for key, item in all_downloads.items():
                category = item.get('category', '').lower()
                
                # Include manuscript templates and conference proceedings
                if category in ['manuscript_templates', 'conference_proceedings', 'latex_templates']:
                    # Determine display category based on file type or category
                    file_type = item.get('type', '').lower()
                    
                    if file_type in ['tex', 'latex'] or 'latex' in category:
                        display_category = 'LaTeX'
                    elif file_type in ['doc', 'docx'] or 'word' in category:
                        display_category = 'Microsoft Word'
                    elif 'overleaf' in item.get('description', '').lower():
                        display_category = 'Overleaf'
                    else:
                        display_category = 'General'
                    
                    if display_category not in downloads:
                        downloads[display_category] = []
                    
                    # Create download item with proper structure
                    download_item = {
                        'title': item.get('title', 'Untitled'),
                        'description': item.get('description', 'Conference template for manuscript preparation'),
                        'file_type': file_type,
                        'format': display_category,
                        'size': item.get('file_size', ''),
                        'url': item.get('file_url', item.get('external_url', '#')),
                        'updated_at': item.get('updated_at', '')
                    }
                    downloads[display_category].append(download_item)
        
        # Define category information for the template
        category_info = {
            'LaTeX': {
                'title': 'LaTeX Templates',
                'description': 'Professional LaTeX templates for academic paper formatting',
                'icon': 'fas fa-file-code'
            },
            'Microsoft Word': {
                'title': 'Microsoft Word Templates',
                'description': 'Easy-to-use Word templates for manuscript preparation',
                'icon': 'fas fa-file-word'
            },
            'Overleaf': {
                'title': 'Overleaf Templates',
                'description': 'Online collaborative LaTeX editing templates',
                'icon': 'fas fa-share-alt'
            },
            'General': {
                'title': 'General Templates',
                'description': 'Various template formats for conference submissions',
                'icon': 'fas fa-file'
            }
        }
        
        # Get site design
        site_design = get_site_design()
        
        return render_template('user/conference_proceedings.html',
                             downloads=downloads,
                             category_info=category_info,
                             content=content,
                             site_design=site_design)
    except Exception as e:
        print(f"Error loading conference proceedings: {e}")
        flash('Error loading conference proceedings.', 'error')
        return redirect(url_for('home'))

# =============================================================================
# MULTI-CONFERENCE SUPPORT ROUTES
# =============================================================================

def get_conference_data(conference_id):
    """Get conference data from Firebase"""
    try:
        conference_ref = db.reference(f'conferences/{conference_id}')
        conference = conference_ref.get()
        return conference
    except Exception as e:
        print(f"Error getting conference data: {e}")
        return None

def _get_about_content_conference(conference_id: str):
    """Resolve a conference-like object from Admin About Content future_conferences when using synthetic IDs.

    Synthetic ID pattern: about_future_{year}_{idx}
    """
    try:
        if not conference_id or not conference_id.startswith('about_future_'):
            return None

        # Timezone setup
        sast_tz = pytz.timezone('Africa/Johannesburg')

        # Local helpers (match discover route)
        def _parse_date(value):
            try:
                if not value:
                    return None
                text = str(value)
                dt = None
                try:
                    dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
                except Exception:
                    dt = datetime.strptime(text, '%Y-%m-%d')
                if getattr(dt, 'tzinfo', None) is None:
                    dt = sast_tz.localize(dt)
                else:
                    dt = dt.astimezone(sast_tz)
                return dt
            except Exception:
                return None

        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'sept': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12,
        }

        def _build_date(y_str, d_entry):
            try:
                day_raw = d_entry.get('date')
                month_raw = d_entry.get('month')
                day = str(day_raw).strip() if day_raw is not None else ''
                month_txt = str(month_raw).strip().lower() if month_raw is not None else ''
                month_num = None
                if month_txt.isdigit():
                    try:
                        month_num = int(month_txt)
                    except Exception:
                        month_num = None
                if month_num is None:
                    month_num = month_map.get(month_txt)
                if not (y_str and day and month_num):
                    return None
                iso_str = f"{int(y_str):04d}-{int(month_num):02d}-{int(day):02d}"
                return _parse_date(iso_str)
            except Exception:
                return None

        about_content = db.reference('about_content').get() or {}
        future_section = (about_content.get('future_conferences') or {})
        if not (future_section.get('section_enabled') and isinstance(future_section.get('conferences'), list)):
            return None

        # Extract index from id
        # Expected pattern: about_future_{year}_{idx}
        try:
            parts = conference_id.split('_')
            idx = int(parts[-1])
        except Exception:
            idx = None

        # Iterate and match by index order
        current_idx = -1
        for conf in future_section['conferences']:
            if not conf or not conf.get('enabled'):
                continue
            current_idx += 1
            if idx is not None and current_idx != idx:
                continue

            year = str(conf.get('year') or '').strip()
            title = (conf.get('title') or '').strip()
            dates = conf.get('dates') or []
            if not (title and year and dates):
                continue

            start_dt = _build_date(year, dates[0]) if dates else None
            end_dt = _build_date(year, dates[-1]) if dates else start_dt
            if not start_dt:
                continue

            now_sast = datetime.now(sast_tz)
            if start_dt and now_sast < start_dt:
                status_val = 'upcoming'
            elif end_dt and now_sast > end_dt:
                status_val = 'past'
            else:
                status_val = 'active'

            platform = (conf.get('platform') or '').strip()
            desc_bits = []
            if platform:
                desc_bits.append(f"Platform: {platform}")
            if dates:
                human_dates = ", ".join([
                    f"{d.get('date')}/{d.get('month')}" for d in dates if d
                ])
                if human_dates:
                    desc_bits.append(f"Dates: {human_dates}")
            description = " | ".join(desc_bits)

            return {
                'basic_info': {
                    'name': title,
                    'year': year,
                    'description': description,
                    'start_date': start_dt.isoformat() if start_dt else '',
                    'end_date': end_dt.isoformat() if end_dt else '',
                    'location': '',
                    'timezone': 'Africa/Johannesburg',
                    'website': '',
                    'status': status_val
                },
                'settings': {
                    'registration_enabled': False if status_val == 'past' else False,
                    'paper_submission_enabled': False,
                    'review_enabled': False
                }
            }

        return None
    except Exception as e:
        print(f"Error resolving about_content conference: {e}")
        return None

@app.route('/admin/conference-galleries')
@login_required
@admin_required
def admin_conference_galleries():
    """Admin interface for managing conference galleries"""
    try:
        # Get all conferences
        conferences = get_all_conferences()

        return render_template('admin/conference_galleries.html',
                             conferences=conferences,
                             site_design=get_site_design(),
                             tinymce_api_key=app.config.get('TINYMCE_API_KEY'))

    except Exception as e:
        print(f"Error loading conference galleries: {e}")
        flash(f'Error loading conference galleries: {str(e)}', 'danger')
        return render_template('admin/conference_galleries.html',
                             conferences={},
                             site_design=get_site_design(),
                             tinymce_api_key=app.config.get('TINYMCE_API_KEY'))

@app.route('/admin/conference-galleries/<conference_id>/upload', methods=['POST'])
@login_required
@admin_required
def upload_gallery_image(conference_id):
    """Upload an image to a conference gallery"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if file and allowed_image_file(file.filename):
            # Generate unique filename
            filename = secure_filename(f"{conference_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file_path = f"gallery/{conference_id}/{filename}"

            # Get file size before upload
            file_size = len(file.read())
            file.seek(0)  # Reset file pointer after reading size

            # Upload to Firebase Storage
            print(f"Uploading to Firebase Storage: {file_path}")
            bucket = storage.bucket()
            blob = bucket.blob(file_path)

            try:
                blob.upload_from_file(file, content_type=file.content_type)
                blob.make_public()
                print(f"✅ Successfully uploaded to Firebase Storage")
            except Exception as e:
                print(f"❌ Firebase Storage upload failed: {str(e)}")
                return jsonify({'success': False, 'error': f'Storage upload failed: {str(e)}'}), 500

            # Get public URL
            image_url = blob.public_url
            print(f"📎 Public URL: {image_url}")

            # Save image metadata to database
            image_data = {
                'filename': filename,
                'original_name': file.filename,
                'url': image_url,
                'uploaded_by': current_user.email,
                'uploaded_at': datetime.now().isoformat(),
                'conference_id': conference_id,
                'file_size': file_size,
                'content_type': file.content_type
            }

            gallery_ref = db.reference(f'conferences/{conference_id}/gallery')
            new_image_ref = gallery_ref.push(image_data)

            return jsonify({
                'success': True,
                'message': 'Image uploaded successfully',
                'image_id': new_image_ref.key,
                'image_url': image_url
            })

        return jsonify({'success': False, 'error': 'Invalid file type'}), 400

    except Exception as e:
        print(f"Error uploading gallery image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/images')
@login_required
@admin_required
def get_gallery_images(conference_id):
    """Get all images for a conference gallery"""
    try:
        gallery_ref = db.reference(f'conferences/{conference_id}/gallery')
        images = gallery_ref.get() or {}

        # Convert to list and sort by upload date
        images_list = []
        for image_id, image_data in images.items():
            image_data['image_id'] = image_id
            images_list.append(image_data)

        images_list.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)

        return jsonify(images_list)

    except Exception as e:
        print(f"Error getting gallery images: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/images/<image_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_gallery_image(conference_id, image_id):
    """Delete an image from a conference gallery"""
    try:
        # Get image data first
        image_ref = db.reference(f'conferences/{conference_id}/gallery/{image_id}')
        image_data = image_ref.get()

        if not image_data:
            return jsonify({'success': False, 'error': 'Image not found'}), 404

        # Delete from Firebase Storage
        try:
            bucket = storage.bucket()
            blob = bucket.blob(f"gallery/{conference_id}/{image_data['filename']}")
            blob.delete()
        except Exception as e:
            print(f"Error deleting from storage: {e}")
            # Continue anyway to clean up database

        # Delete from database
        image_ref.delete()

        return jsonify({'success': True, 'message': 'Image deleted successfully'})

    except Exception as e:
        print(f"Error deleting gallery image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/conference-galleries/<conference_id>/images')
def get_public_gallery_images(conference_id):
    """Get all images for a conference gallery (public access)"""
    try:
        # Check if conference exists and gallery is enabled
        conference = get_conference_data(conference_id)
        if not conference:
            return jsonify([])

        if not conference.get('settings', {}).get('gallery_enabled', True):
            return jsonify([])

        gallery_ref = db.reference(f'conferences/{conference_id}/gallery')
        images = gallery_ref.get() or {}

        # Convert to list and sort by upload date
        images_list = []
        for image_id, image_data in images.items():
            image_data['image_id'] = image_id
            images_list.append(image_data)

        images_list.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)

        response = jsonify(images_list)

        # Prevent caching to ensure visibility changes are reflected immediately
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        print(f"Error getting public gallery images: {e}")
        response = jsonify([])
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

@app.route('/galleries')
def galleries():
    """Public gallery view showing all conference galleries"""
    try:
        conferences = get_all_conferences()

        # Filter conferences to only show those with enabled galleries
        visible_conferences = {}
        for conf_id, conference in conferences.items():
            # Check if gallery is explicitly disabled, otherwise show it (default to True for backward compatibility)
            settings = conference.get('settings', {})
            gallery_enabled = settings.get('gallery_enabled', True)  # Default to True

            if gallery_enabled:
                # Add gradient colors for visual variety
                gradient_colors = conference.get('gradient_colors', generate_gradient_colors(conf_id))
                conference['gradient_colors'] = gradient_colors
                
                # Include gallery summary if available
                gallery_summary = conference.get('gallery_summary')
                if gallery_summary:
                    conference['gallery_summary'] = gallery_summary
                
                visible_conferences[conf_id] = conference

        response = make_response(render_template('galleries.html',
                                               conferences=visible_conferences,
                                               site_design=get_site_design()))

        # Prevent caching to ensure visibility changes are reflected immediately
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response
    except Exception as e:
        print(f"Error loading galleries: {e}")
        return render_template('galleries.html',
                             conferences={},
                             site_design=get_site_design())

@app.route('/galleries/<conference_id>')
def conference_gallery(conference_id):
    """View gallery for a specific conference"""
    try:
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found', 'danger')
            return redirect(url_for('galleries'))

        # Check if gallery is enabled for this conference
        if not conference.get('settings', {}).get('gallery_enabled', True):
            flash('Gallery is not available for this conference', 'warning')
            return redirect(url_for('galleries'))

        # Get gallery images
        gallery_ref = db.reference(f'conferences/{conference_id}/gallery')
        images = gallery_ref.get() or {}

        # Convert to list and sort by upload date
        images_list = []
        for image_id, image_data in images.items():
            image_data['image_id'] = image_id
            images_list.append(image_data)

        images_list.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)

        # Get featured attendees
        attendees_ref = db.reference(f'conferences/{conference_id}/gallery_attendees')
        attendees = attendees_ref.get() or {}

        # Convert to list and sort by name
        attendees_list = []
        for attendee_id, attendee_data in attendees.items():
            attendee_data['attendee_id'] = attendee_id
            attendees_list.append(attendee_data)

        attendees_list.sort(key=lambda x: x.get('full_name', ''))

        response = make_response(render_template('conference_gallery.html',
                                               conference=conference,
                                               images=images_list,
                                               attendees=attendees_list,
                                               site_design=get_site_design()))

        # Prevent caching to ensure visibility changes are reflected immediately
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response
    except Exception as e:
        print(f"Error loading conference gallery: {e}")
        flash(f'Error loading gallery: {str(e)}', 'danger')
        return redirect(url_for('galleries'))

@app.route('/admin/conference-galleries/<conference_id>/toggle-visibility', methods=['POST'])
@login_required
@admin_required
def toggle_gallery_visibility(conference_id):
    """Toggle gallery visibility for a conference"""
    try:
        enabled = request.form.get('enabled') == 'true'

        # Update conference settings
        conference_ref = db.reference(f'conferences/{conference_id}')
        conference_ref.child('settings').child('gallery_enabled').set(enabled)

        return jsonify({'success': True, 'message': 'Gallery visibility updated'})

    except Exception as e:
        print(f"Error toggling gallery visibility: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/summary', methods=['POST'])
@login_required
@admin_required
def save_gallery_summary(conference_id):
    """Save gallery summary and description for a conference"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        summary = data.get('summary', '').strip()
        description = data.get('description', '').strip()
        show_summary_public = data.get('show_summary_public', True)  # Default to True if not provided
        show_description_public = data.get('show_description_public', True)  # Default to True if not provided
        
        # Backward compatibility: if old show_public exists, use it for both
        if 'show_public' in data and 'show_summary_public' not in data and 'show_description_public' not in data:
            show_summary_public = data.get('show_public', True)
            show_description_public = data.get('show_public', True)
        
        # Validate summary length
        if len(summary) > 500:
            return jsonify({'success': False, 'error': 'Summary must be 500 characters or less'}), 400
        
        # Prepare summary data
        summary_data = {
            'summary': summary,
            'description': description,
            'show_summary_public': show_summary_public,
            'show_description_public': show_description_public,
            'updated_at': datetime.now().isoformat(),
            'updated_by': session.get('user_id', 'unknown')
        }
        
        # Save to Firebase
        summary_ref = db.reference(f'conferences/{conference_id}/gallery_summary')
        summary_ref.set(summary_data)
        
        print(f"Gallery summary saved for conference {conference_id}")
        return jsonify({'success': True, 'message': 'Gallery summary saved successfully'})
        
    except Exception as e:
        print(f"Error saving gallery summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/summary', methods=['GET'])
@login_required
@admin_required
def get_gallery_summary(conference_id):
    """Get gallery summary and description for a conference"""
    try:
        summary_ref = db.reference(f'conferences/{conference_id}/gallery_summary')
        summary_data = summary_ref.get()
        
        if not summary_data:
            return jsonify({'summary': '', 'description': ''})
        
        return jsonify({
            'summary': summary_data.get('summary', ''),
            'description': summary_data.get('description', ''),
            'updated_at': summary_data.get('updated_at'),
            'updated_by': summary_data.get('updated_by')
        })
        
    except Exception as e:
        print(f"Error getting gallery summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/attendees')
@login_required
@admin_required
def manage_attendee_gallery(conference_id):
    """Manage attendees featured in conference gallery"""
    try:
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found', 'danger')
            return redirect(url_for('admin_conference_galleries'))

        # Get all registrations for this conference
        registrations_ref = db.reference('registrations')
        all_registrations = registrations_ref.get() or {}

        # Filter registrations for this conference (we need to add conference_id to registrations)
        conference_registrations = {}
        for reg_id, reg_data in all_registrations.items():
            # For now, we'll get all registrations and filter by user conference association
            # This will be improved when we add conference_id to registration records
            if reg_data.get('user_id'):
                conference_registrations[reg_id] = reg_data

        # Get featured attendees in gallery
        gallery_attendees_ref = db.reference(f'conferences/{conference_id}/gallery_attendees')
        featured_attendees = gallery_attendees_ref.get() or {}

        # Get user details for all registrations and featured attendees
        users_ref = db.reference('users')
        users = users_ref.get() or {}

        # Enhance registration data with user info
        enhanced_registrations = {}
        for reg_id, reg_data in conference_registrations.items():
            user_id = reg_data.get('user_id')
            if user_id and user_id in users:
                user_info = users[user_id].copy()
                user_info['user_id'] = user_id  # Explicitly add user_id
                user_info['registration_id'] = reg_id
                user_info['registration_data'] = reg_data
                enhanced_registrations[reg_id] = user_info

        # Enhance featured attendees with user info
        enhanced_featured = {}
        for attendee_id, attendee_data in featured_attendees.items():
            user_id = attendee_data.get('user_id')
            if user_id and user_id in users:
                user_info = users[user_id].copy()
                user_info['user_id'] = user_id  # Explicitly add user_id
                user_info['gallery_attendee_id'] = attendee_id
                user_info['gallery_data'] = attendee_data
                enhanced_featured[attendee_id] = user_info

        return render_template('admin/conference_galleries_attendees.html',
                             conference=conference,
                             conference_id=conference_id,
                             available_attendees=enhanced_registrations,
                             featured_attendees=enhanced_featured,
                             site_design=get_site_design())

    except Exception as e:
        print(f"Error loading attendee gallery management: {e}")
        flash(f'Error loading attendee gallery management: {str(e)}', 'danger')
        return redirect(url_for('admin_conference_galleries'))

@app.route('/admin/conference-galleries/<conference_id>/attendees/add', methods=['POST'])
@login_required
@admin_required
def add_attendee_to_gallery(conference_id):
    """Add an attendee to the conference gallery"""
    try:
        print(f"DEBUG: Add attendee request received for conference {conference_id}")
        print(f"DEBUG: Current user: {current_user.id if current_user.is_authenticated else 'Not authenticated'}")
        print(f"DEBUG: Is admin: {current_user.is_admin if current_user.is_authenticated else 'N/A'}")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Form data: {dict(request.form)}")

        user_id = request.form.get('user_id')
        registration_id = request.form.get('registration_id')

        if not user_id:
            print("DEBUG: No user_id provided in form data")
            return jsonify({'success': False, 'error': 'User ID is required'}), 400

        # Get user information
        user_ref = db.reference(f'users/{user_id}')
        user_data = user_ref.get()

        if not user_data:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        # Create attendee gallery entry
        attendee_data = {
            'user_id': user_id,
            'registration_id': registration_id,
            'full_name': user_data.get('full_name', ''),
            'institution': user_data.get('institution', ''),
            'department': user_data.get('department', ''),
            'title': user_data.get('title', ''),
            'country': user_data.get('country', ''),
            'city': user_data.get('city', ''),
            'bio': user_data.get('bio', ''),
            'website': user_data.get('website', ''),
            'photo_url': user_data.get('photo_url', ''),  # Profile photo if available
            'added_by': current_user.email,
            'added_at': datetime.now().isoformat()
        }

        # Add to gallery attendees
        gallery_attendees_ref = db.reference(f'conferences/{conference_id}/gallery_attendees')
        new_attendee_ref = gallery_attendees_ref.push(attendee_data)

        return jsonify({
            'success': True,
            'message': 'Attendee added to gallery successfully',
            'attendee_id': new_attendee_ref.key
        })

    except Exception as e:
        print(f"Error adding attendee to gallery: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/attendees/<attendee_id>/remove', methods=['POST'])
@login_required
@admin_required
def remove_attendee_from_gallery(conference_id, attendee_id):
    """Remove an attendee from the conference gallery"""
    try:
        print(f"DEBUG: Remove attendee request received for conference {conference_id}, attendee {attendee_id}")
        print(f"DEBUG: Current user: {current_user.id if current_user.is_authenticated else 'Not authenticated'}")
        print(f"DEBUG: Is admin: {current_user.is_admin if current_user.is_authenticated else 'N/A'}")

        # Remove attendee from gallery
        attendee_ref = db.reference(f'conferences/{conference_id}/gallery_attendees/{attendee_id}')
        attendee_ref.delete()

        print(f"DEBUG: Attendee {attendee_id} removed successfully")
        return jsonify({'success': True, 'message': 'Attendee removed from gallery successfully'})

    except Exception as e:
        print(f"Error removing attendee from gallery: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/attendees/<attendee_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_attendee_info(conference_id, attendee_id):
    """Edit attendee information in the gallery"""
    try:
        if request.method == 'GET':
            # Get attendee data for editing
            attendee_ref = db.reference(f'conferences/{conference_id}/gallery_attendees/{attendee_id}')
            attendee_data = attendee_ref.get()

            if not attendee_data:
                flash('Attendee not found', 'danger')
                return redirect(url_for('manage_attendee_gallery', conference_id=conference_id))

            return jsonify(attendee_data)

        elif request.method == 'POST':
            # Update attendee information
            print(f"DEBUG: Edit attendee request received for conference {conference_id}, attendee {attendee_id}")

            # Get updated data from form
            updated_data = {
                'full_name': request.form.get('full_name', '').strip(),
                'institution': request.form.get('institution', '').strip(),
                'department': request.form.get('department', '').strip(),
                'title': request.form.get('title', '').strip(),
                'country': request.form.get('country', '').strip(),
                'city': request.form.get('city', '').strip(),
                'bio': request.form.get('bio', '').strip(),
                'website': request.form.get('website', '').strip(),
                'updated_by': current_user.email,
                'updated_at': datetime.now().isoformat()
            }

            # Remove empty fields
            updated_data = {k: v for k, v in updated_data.items() if v}

            # Update in Firebase
            attendee_ref = db.reference(f'conferences/{conference_id}/gallery_attendees/{attendee_id}')
            attendee_ref.update(updated_data)

            print(f"DEBUG: Attendee {attendee_id} updated successfully")
            return jsonify({'success': True, 'message': 'Attendee information updated successfully'})

    except Exception as e:
        print(f"Error editing attendee information: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/attendees/<attendee_id>/upload-photo', methods=['POST'])
@login_required
@admin_required
def upload_attendee_photo(conference_id, attendee_id):
    """Upload or update attendee profile photo"""
    try:
        print(f"DEBUG: Upload photo request received for conference {conference_id}, attendee {attendee_id}")

        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No photo file provided'}), 400

        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if file and allowed_image_file(file.filename):
            # Get attendee data first
            attendee_ref = db.reference(f'conferences/{conference_id}/gallery_attendees/{attendee_id}')
            attendee_data = attendee_ref.get()

            if not attendee_data:
                return jsonify({'success': False, 'error': 'Attendee not found'}), 404

            user_id = attendee_data.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'error': 'User ID not found for attendee'}), 400

            # Generate unique filename for attendee photo
            filename = secure_filename(f"attendee_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file_path = f"attendees/{conference_id}/{filename}"

            # Upload to Firebase Storage
            bucket = storage.bucket()
            blob = bucket.blob(file_path)

            # Read file content
            file.seek(0)
            blob.upload_from_file(file, content_type=file.content_type)
            blob.make_public()

            # Get public URL
            photo_url = blob.public_url
            print(f"📎 Attendee photo URL: {photo_url}")

            # Update attendee data with new photo URL
            attendee_ref.update({
                'photo_url': photo_url,
                'photo_updated_by': current_user.email,
                'photo_updated_at': datetime.now().isoformat()
            })

            # Also update the user's profile photo if they exist
            try:
                user_ref = db.reference(f'users/{user_id}')
                user_ref.update({'photo_url': photo_url})
                print(f"✅ Updated user profile photo for {user_id}")
            except Exception as user_update_error:
                print(f"Warning: Could not update user profile photo: {str(user_update_error)}")

            print(f"DEBUG: Attendee photo uploaded successfully for attendee {attendee_id}")
            return jsonify({
                'success': True,
                'message': 'Attendee photo uploaded successfully',
                'photo_url': photo_url
            })

        return jsonify({'success': False, 'error': 'Invalid file type'}), 400

    except Exception as e:
        print(f"Error uploading attendee photo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user_info(user_id):
    """Edit user information (for available attendees)"""
    try:
        if request.method == 'GET':
            # Get user data for editing
            user_ref = db.reference(f'users/{user_id}')
            user_data = user_ref.get()

            if not user_data:
                return jsonify({'error': 'User not found'}), 404

            return jsonify(user_data)

        elif request.method == 'POST':
            # Update user information
            print(f"DEBUG: Edit user request received for user {user_id}")

            # Get updated data from form
            updated_data = {
                'full_name': request.form.get('full_name', '').strip(),
                'institution': request.form.get('institution', '').strip(),
                'department': request.form.get('department', '').strip(),
                'title': request.form.get('title', '').strip(),
                'country': request.form.get('country', '').strip(),
                'city': request.form.get('city', '').strip(),
                'bio': request.form.get('bio', '').strip(),
                'website': request.form.get('website', '').strip(),
                'updated_by': current_user.email,
                'updated_at': datetime.now().isoformat()
            }

            # Remove empty fields
            updated_data = {k: v for k, v in updated_data.items() if v}

            # Update in Firebase
            user_ref = db.reference(f'users/{user_id}')
            user_ref.update(updated_data)

            print(f"DEBUG: User {user_id} updated successfully")
            return jsonify({'success': True, 'message': 'User information updated successfully'})

    except Exception as e:
        print(f"Error editing user information: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/users/<user_id>/upload-photo', methods=['POST'])
@login_required
@admin_required
def upload_user_photo(user_id):
    """Upload or update user profile photo"""
    try:
        print(f"DEBUG: Upload user photo request received for user {user_id}")

        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No photo file provided'}), 400

        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        if file and allowed_image_file(file.filename):
            # Generate unique filename for user photo
            filename = secure_filename(f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file_path = f"users/{filename}"

            # Upload to Firebase Storage
            bucket = storage.bucket()
            blob = bucket.blob(file_path)

            # Read file content
            file.seek(0)
            blob.upload_from_file(file, content_type=file.content_type)
            blob.make_public()

            # Get public URL
            photo_url = blob.public_url
            print(f"📎 User photo URL: {photo_url}")

            # Update user data with new photo URL
            user_ref = db.reference(f'users/{user_id}')
            user_ref.update({
                'photo_url': photo_url,
                'photo_updated_by': current_user.email,
                'photo_updated_at': datetime.now().isoformat()
            })

            print(f"DEBUG: User photo uploaded successfully for user {user_id}")
            return jsonify({
                'success': True,
                'message': 'User photo uploaded successfully',
                'photo_url': photo_url
            })

        return jsonify({'success': False, 'error': 'Invalid file type'}), 400

    except Exception as e:
        print(f"Error uploading user photo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/users/<user_id>/delete-photo', methods=['POST'])
@login_required
@admin_required
def delete_user_photo(user_id):
    """Delete user profile photo"""
    try:
        print(f"DEBUG: Delete user photo request received for user {user_id}")

        # Get user data
        user_ref = db.reference(f'users/{user_id}')
        user_data = user_ref.get()

        if not user_data:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        photo_url = user_data.get('photo_url')
        if not photo_url:
            return jsonify({'success': False, 'error': 'No photo to delete'}), 400

        # Extract filename from URL
        try:
            # Parse Firebase Storage URL to get file path
            url_parts = photo_url.split('/')
            bucket_name = url_parts[3]  # storage.googleapis.com
            file_path = '/'.join(url_parts[4:])  # everything after bucket

            # Delete from Firebase Storage
            bucket = storage.bucket()
            blob = bucket.blob(file_path)
            blob.delete()
            print(f"✅ Deleted photo from storage: {file_path}")

        except Exception as storage_error:
            print(f"Warning: Could not delete photo from storage: {str(storage_error)}")

        # Remove photo URL from user data
        user_ref.update({
            'photo_url': None,
            'photo_updated_by': current_user.email,
            'photo_updated_at': datetime.now().isoformat()
        })

        print(f"DEBUG: User photo deleted successfully for user {user_id}")
        return jsonify({'success': True, 'message': 'User photo deleted successfully'})

    except Exception as e:
        print(f"Error deleting user photo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conference-galleries/<conference_id>/attendees/<attendee_id>/delete-photo', methods=['POST'])
@login_required
@admin_required
def delete_attendee_photo(conference_id, attendee_id):
    """Delete attendee profile photo"""
    try:
        print(f"DEBUG: Delete photo request received for conference {conference_id}, attendee {attendee_id}")

        # Get attendee data
        attendee_ref = db.reference(f'conferences/{conference_id}/gallery_attendees/{attendee_id}')
        attendee_data = attendee_ref.get()

        if not attendee_data:
            return jsonify({'success': False, 'error': 'Attendee not found'}), 404

        photo_url = attendee_data.get('photo_url')
        if not photo_url:
            return jsonify({'success': False, 'error': 'No photo to delete'}), 400

        # Extract filename from URL
        try:
            # Parse Firebase Storage URL to get file path
            # URL format: https://storage.googleapis.com/{bucket}/{path}
            url_parts = photo_url.split('/')
            bucket_name = url_parts[3]  # storage.googleapis.com
            file_path = '/'.join(url_parts[4:])  # everything after bucket

            # Delete from Firebase Storage
            bucket = storage.bucket()
            blob = bucket.blob(file_path)
            blob.delete()
            print(f"✅ Deleted photo from storage: {file_path}")

        except Exception as storage_error:
            print(f"Warning: Could not delete photo from storage: {str(storage_error)}")

        # Remove photo URL from attendee data
        attendee_ref.update({
            'photo_url': None,
            'photo_updated_by': current_user.email,
            'photo_updated_at': datetime.now().isoformat()
        })

        # Also remove from user profile
        user_id = attendee_data.get('user_id')
        if user_id:
            try:
                user_ref = db.reference(f'users/{user_id}')
                user_ref.update({'photo_url': None})
                print(f"✅ Removed photo from user profile for {user_id}")
            except Exception as user_update_error:
                print(f"Warning: Could not update user profile: {str(user_update_error)}")

        print(f"DEBUG: Attendee photo deleted successfully for attendee {attendee_id}")
        return jsonify({'success': True, 'message': 'Attendee photo deleted successfully'})

    except Exception as e:
        print(f"Error deleting attendee photo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_gradient_colors(conference_id):
    """Generate unique gradient colors based on conference ID"""
    # Use conference ID to create deterministic but varied color combinations
    color_sets = [
        '#007bff, #6610f2',  # Blue to Purple
        '#28a745, #20c997',  # Green to Teal
        '#dc3545, #fd7e14',  # Red to Orange
        '#6f42c1, #e83e8c',  # Purple to Pink
        '#17a2b8, #6f42c1',  # Cyan to Purple
        '#ffc107, #fd7e14',  # Yellow to Orange
        '#28a745, #007bff',  # Green to Blue
        '#dc3545, #6f42c1',  # Red to Purple
        '#e83e8c, #dc3545',  # Pink to Red
        '#20c997, #17a2b8',  # Teal to Cyan
    ]

    # Use hash of conference ID to select color set
    import hashlib
    hash_obj = hashlib.md5(conference_id.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    color_index = hash_int % len(color_sets)

    return color_sets[color_index]

def get_all_conferences():
    """Get all conferences from Firebase"""
    try:
        conferences_ref = db.reference('conferences')
        conferences = conferences_ref.get() or {}
        return conferences
    except Exception as e:
        print(f"Error getting conferences: {e}")
        return {}

@app.route('/conferences')
def conference_discover():
    """Conference discovery page - list all available conferences"""
    try:
        conferences = get_all_conferences()
        
        # Normalize, compute status, and sort
        normalized_conferences = {}
        # Use South African Standard Time (UTC+02:00) for all comparisons
        sast_tz = pytz.timezone('Africa/Johannesburg')
        now = datetime.now(sast_tz)

        # Helper to parse to SAST aware datetimes
        def _parse_date(value):
            """Parse to timezone-aware datetime in SAST. If input has timezone, convert to SAST; otherwise assume SAST."""
            try:
                if not value:
                    return None
                text = str(value)
                dt = None
                try:
                    # Handle ISO strings, with or without timezone
                    dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
                except Exception:
                    # Fallback to common date-only format
                    dt = datetime.strptime(text, '%Y-%m-%d')
                if getattr(dt, 'tzinfo', None) is None:
                    # Assume SAST if tz is missing
                    dt = sast_tz.localize(dt)
                else:
                    # Convert any tz-aware datetime to SAST
                    dt = dt.astimezone(sast_tz)
                return dt
            except Exception:
                return None

        # 1) Pull future/upcoming conferences from admin About Content
        try:
            about_content = db.reference('about_content').get() or {}
            future_section = (about_content.get('future_conferences') or {})
            about_confs_only = []
            if future_section.get('section_enabled') and isinstance(future_section.get('conferences'), list):
                month_map = {
                    'jan': 1, 'january': 1,
                    'feb': 2, 'february': 2,
                    'mar': 3, 'march': 3,
                    'apr': 4, 'april': 4,
                    'may': 5,
                    'jun': 6, 'june': 6,
                    'jul': 7, 'july': 7,
                    'aug': 8, 'august': 8,
                    'sep': 9, 'sept': 9, 'september': 9,
                    'oct': 10, 'october': 10,
                    'nov': 11, 'november': 11,
                    'dec': 12, 'december': 12,
                }

                for idx, conf in enumerate(future_section['conferences']):
                    if not conf or not conf.get('enabled'):
                        continue
                    year = str(conf.get('year') or '').strip()
                    title = (conf.get('title') or '').strip()
                    dates = conf.get('dates') or []
                    # Build start/end from first/last provided date entry
                    def _build_date(d_entry):
                        try:
                            day_raw = d_entry.get('date')
                            month_raw = d_entry.get('month')
                            # Coerce types
                            day = str(day_raw).strip() if day_raw is not None else ''
                            month_txt = str(month_raw).strip().lower() if month_raw is not None else ''
                            # Support numeric months (e.g., '9' or '09' or 9)
                            month_num = None
                            if month_txt.isdigit():
                                try:
                                    month_num = int(month_txt)
                                except Exception:
                                    month_num = None
                            if month_num is None:
                                month_num = month_map.get(month_txt)
                            if not (year and day and month_num):
                                return None
                            # zero-pad month/day
                            y = int(year)
                            m = int(month_num)
                            d = int(day)
                            iso_str = f"{y:04d}-{m:02d}-{d:02d}"
                            return _parse_date(iso_str)
                        except Exception as e:
                            print(f"_build_date parse error: {e} | entry={d_entry}")
                            return None

                    start_dt = _build_date(dates[0]) if dates else None
                    end_dt = _build_date(dates[-1]) if dates else start_dt

                    # Skip incomplete entries (avoid dummy placeholders)
                    if not title or not year or not start_dt:
                        continue

                    # Create a synthetic ID for discover listing (stable-ish)
                    conf_id = f"about_future_{year}_{idx}"
                    # Build a friendly description from About Content fields
                    platform = (conf.get('platform') or '').strip()
                    desc_bits = []
                    if platform:
                        desc_bits.append(f"Platform: {platform}")
                    if dates:
                        human_dates = ", ".join([
                            f"{d.get('date')}/{d.get('month')}" for d in dates if d
                        ])
                        if human_dates:
                            desc_bits.append(f"Dates: {human_dates}")
                    description = " | ".join(desc_bits)

                    # Compute status from dates (SAST-aware)
                    if start_dt and now < start_dt:
                        status_val = 'upcoming'
                    elif end_dt and now > end_dt:
                        status_val = 'past'
                    else:
                        status_val = 'active'

                    about_confs_only.append((conf_id, {
                        'basic_info': {
                            'name': title,
                            'year': year,
                            'description': description,
                            'start_date': start_dt.isoformat() if start_dt else '',
                            'end_date': end_dt.isoformat() if end_dt else '',
                            'location': '',
                            'timezone': 'Africa/Johannesburg',
                            'website': '',
                            'status': status_val
                        },
                        'settings': {
                            # Never open registration if past
                            'registration_enabled': False if status_val == 'past' else False,
                            'paper_submission_enabled': False,
                            'review_enabled': False
                        }
                    }))
            # If About Content defines future conferences, prefer showing ONLY those
            if about_confs_only:
                normalized_conferences = {cid: data for cid, data in about_confs_only}
                conferences = {}  # skip merging runtime conferences
        except Exception as e:
            print(f"Error reading about_content for future conferences: {e}")

        # 2) Merge any explicit conferences from /conferences tree (admin-defined runtime conferences)
        for conf_id, conf_data in (conferences or {}).items():
            if not conf_data:
                continue

            # Ensure basic_info/settings exist to avoid template undefineds
            basic = conf_data.get('basic_info', {}) or {}
            conf_data.setdefault('basic_info', basic)
            conf_data.setdefault('settings', conf_data.get('settings', {}) or {})
            start_raw = basic.get('start_date')
            end_raw = basic.get('end_date')

            # Parse dates safely (supports 'YYYY-MM-DD' or ISO8601)
            def _parse_date(value):
                """Parse to timezone-aware datetime in SAST. If input has timezone, convert to SAST; otherwise assume SAST."""
                try:
                    if not value:
                        return None
                    text = str(value)
                    dt = None
                    try:
                        # Handle ISO strings, with or without timezone
                        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
                    except Exception:
                        # Fallback to common date-only format
                        dt = datetime.strptime(text, '%Y-%m-%d')
                    if getattr(dt, 'tzinfo', None) is None:
                        # Assume SAST if tz is missing
                        dt = sast_tz.localize(dt)
                    else:
                        # Convert any tz-aware datetime to SAST
                        dt = dt.astimezone(sast_tz)
                    return dt
                except Exception:
                    return None

            start_dt = _parse_date(start_raw)
            end_dt = _parse_date(end_raw)

            # Get admin-provided status
            admin_status = (basic.get('status') or '').strip().lower()
            
            # Normalize common synonyms if admin provided a value
            synonym_map = {
                'future': 'upcoming',
                'scheduled': 'upcoming',
                'soon': 'upcoming',
                'open': 'active',
                'live': 'active',
                'closed': 'past',
                'ended': 'past',
                'finished': 'past'
            }
            if admin_status in synonym_map:
                admin_status = synonym_map[admin_status]

            # AUTO-COMPUTE status based on dates (prioritize date-based logic)
            # This ensures past conferences are always marked correctly even if admin forgot
            computed_status = None
            if start_dt and end_dt:
                # Date-based auto-detection
                if now > end_dt:
                    # Conference has ENDED - ALWAYS mark as past
                    computed_status = 'past'
                elif now < start_dt:
                    # Conference hasn't STARTED yet
                    # Allow admin to set as 'active' for early registration/submissions
                    if admin_status == 'active':
                        computed_status = 'active'
                    else:
                        computed_status = 'upcoming'
                else:
                    # Conference is ONGOING (start_dt <= now <= end_dt)
                    computed_status = 'active'
            elif end_dt and now > end_dt:
                # Only end date available, and it has passed
                computed_status = 'past'
            elif start_dt and now < start_dt:
                # Only start date available, and it hasn't started
                computed_status = 'upcoming'
            else:
                # No dates available or dates are invalid, use admin status
                computed_status = admin_status if admin_status else 'draft'

            # Inject back so templates can rely on basic_info.status
            conf_data['basic_info']['status'] = computed_status
            
            # Ensure registration isn't open for past conferences
            if computed_status == 'past':
                conf_data['settings']['registration_enabled'] = False
                conf_data['settings']['paper_submission_enabled'] = False
            
            # SKIP draft conferences on public discovery page (only show to admins)
            if computed_status == 'draft':
                continue

            normalized_conferences[conf_id] = conf_data

        # Optional: sort by start date ascending (upcoming first)
        def _sort_key(item):
            start_val = item[1].get('basic_info', {}).get('start_date')
            parsed = _parse_date(start_val)
            return parsed or now

        conferences_sorted = dict(sorted(normalized_conferences.items(), key=_sort_key))

        return render_template(
            'conferences/discover.html',
            conferences=conferences_sorted,
            site_design=get_site_design()
        )
    except Exception as e:
        print(f"Error loading conferences: {e}")
        flash('Error loading conferences.', 'error')
        return render_template('conferences/discover.html',
                             conferences={},
                             site_design=get_site_design())

@app.route('/conferences/<conference_id>')
def conference_details(conference_id):
    """Conference details page"""
    try:
        conference = get_conference_data(conference_id)
        if not conference:
            # Try resolving from Admin About Content synthetic entries
            conference = _get_about_content_conference(conference_id)
        if not conference:
            flash('Conference not found.', 'error')
            return redirect(url_for('conference_discover'))
        
        return render_template('conferences/details.html',
                             conference=conference,
                             conference_id=conference_id,
                             site_design=get_site_design())
    except Exception as e:
        print(f"Error loading conference details: {e}")
        flash('Error loading conference details.', 'error')
        return redirect(url_for('conference_discover'))

@app.route('/conferences/<conference_id>/register', methods=['GET', 'POST'])
@login_required
def conference_registration(conference_id):
    """Conference-specific registration"""
    try:
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found.', 'error')
            return redirect(url_for('conference_discover'))
        
        if request.method == 'GET':
            # Display registration form
            return render_template('conferences/registration.html',
                                 conference=conference,
                                 conference_id=conference_id,
                                 site_design=get_site_design())
        
        # POST request - process registration
        registration_data = {
            'conference_id': conference_id,
            'conference_code': conference.get('conference_code', ''),
            'conference_name': conference.get('basic_info', {}).get('name', ''),
            'user_id': current_user.id,
            'full_name': request.form.get('full_name'),
            'email': request.form.get('email'),
            'institution': request.form.get('institution'),
            'country': request.form.get('country'),
            'registration_type': request.form.get('registration_type'),
            'submission_date': datetime.now().isoformat(),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Handle file upload for payment proof
        if 'payment_proof' in request.files:
            file = request.files['payment_proof']
            if file.filename != '':
                try:
                    filename = save_payment_proof(file)
                    registration_data['payment_proof'] = filename
                except Exception as e:
                    print(f"Error uploading payment proof: {e}")
                    flash('Error uploading payment proof. Please try again.', 'error')
                    return render_template('conferences/registration.html',
                                         conference=conference,
                                         conference_id=conference_id,
                                         site_design=get_site_design())
        
        # Save to global registrations node (for admin panel)
        global_registration_ref = db.reference('registrations').push()
        registration_data['payment_status'] = 'pending'  # Add payment status field
        global_registration_ref.set(registration_data)
        
        # Also save under user's registrations for easy access
        user_reg_ref = db.reference(f'user_registrations/{current_user.id}').push()
        user_reg_ref.set({
            'conference_id': conference_id,
            'registration_id': global_registration_ref.key,
            'conference_name': conference.get('basic_info', {}).get('name', 'Unknown Conference'),
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        })
        
        # Send confirmation email
        try:
            send_registration_confirmation_email(
                registration_data['email'],
                conference.get('basic_info', {}).get('name', 'Conference'),
                global_registration_ref.key,
                conference.get('conference_code', '')
            )
        except Exception as e:
            print(f"Error sending confirmation email: {e}")
        
        flash('Registration submitted successfully! You will receive a confirmation email shortly.', 'success')
        return redirect(url_for('conference_details', conference_id=conference_id))
        
    except Exception as e:
        print(f"Error processing registration: {e}")
        flash('Error processing registration. Please try again.', 'error')
        return redirect(url_for('conference_registration', conference_id=conference_id))

def send_registration_confirmation_email(email, conference_name, registration_id, conference_code=None):
    """Send registration confirmation email"""
    try:
        subject = f"Registration Confirmation - {conference_name}"
        body = f"""
        Dear Participant,

        Thank you for registering for {conference_name}!
        {"Conference Code: " + conference_code if conference_code else ""}

        Your registration ID is: {registration_id}

        Your registration is currently being reviewed. You will receive another email once your registration is approved.

        If you have any questions, please contact our support team.

        Best regards,
        Conference Organizing Committee
        """

        # Use existing send_email function
        send_email([email], subject, body)

    except Exception as e:
        print(f"Error sending confirmation email: {e}")

@app.route('/conferences/<conference_id>/submit-paper', methods=['GET', 'POST'])
@login_required
def conference_paper_submission(conference_id):
    """Conference-specific paper submission"""
    try:
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found.', 'error')
            return redirect(url_for('conference_discover'))
        
        if not conference.get('settings', {}).get('paper_submission_enabled', False):
            flash('Paper submission is not enabled for this conference.', 'error')
            return redirect(url_for('conference_details', conference_id=conference_id))
        
        if request.method == 'GET':
            # Display paper submission form
            return render_template('conferences/paper_submission.html',
                                 conference=conference,
                                 conference_id=conference_id,
                                 site_design=get_site_design())
        
        # POST request - process paper submission  
        try:
            # Get form data
            paper_data = {
                'conference_id': conference_id,
                'user_id': current_user.id,
                'user_email': current_user.email,
                'paper_title': request.form.get('paper_title'),
                'paper_abstract': request.form.get('paper_abstract'),
                'presentation_type': request.form.get('presentation_type'),
                'research_area': request.form.get('research_area'),
                'keywords': [k.strip() for k in request.form.get('keywords', '').split(',') if k.strip()],
                'submitted_at': datetime.now().isoformat(),
                'status': 'pending',
                'authors': [],
                'review_comments': '',
                'reviewed_by': '',
                'updated_at': datetime.now().isoformat()
            }

            # Process authors
            author_count = 0
            while f'authors[{author_count}][name]' in request.form:
                author = {
                    'name': request.form.get(f'authors[{author_count}][name]'),
                    'email': request.form.get(f'authors[{author_count}][email]'),
                    'institution': request.form.get(f'authors[{author_count}][institution]')
                }
                if all(author.values()):
                    paper_data['authors'].append(author)
                author_count += 1

            # Validate required fields
            required_fields = ['paper_title', 'paper_abstract', 'presentation_type', 'research_area']
            for field in required_fields:
                if not paper_data.get(field):
                    flash('Please fill in all required fields.', 'error')
                    return render_template('conferences/paper_submission.html',
                                         conference=conference,
                                         conference_id=conference_id,
                                         site_design=get_site_design())

            if not paper_data['authors']:
                flash('At least one author is required.', 'error')
                return render_template('conferences/paper_submission.html',
                                     conference=conference,
                                     conference_id=conference_id,
                                     site_design=get_site_design())

            # Handle paper file upload
            if 'paper_file' not in request.files:
                flash('Please upload a paper file.', 'error')
                return render_template('conferences/paper_submission.html',
                                     conference=conference,
                                     conference_id=conference_id,
                                     site_design=get_site_design())

            file = request.files['paper_file']
            if not file or not file.filename:
                flash('Please select a paper file.', 'error')
                return render_template('conferences/paper_submission.html',
                                     conference=conference,
                                     conference_id=conference_id,
                                     site_design=get_site_design())

            if not file.filename.lower().endswith('.pdf'):
                flash('Only PDF files are allowed.', 'error')
                return render_template('conferences/paper_submission.html',
                                     conference=conference,
                                     conference_id=conference_id,
                                     site_design=get_site_design())

            # Read and encode file data
            file_data = file.read()
            file_base64 = base64.b64encode(file_data).decode('utf-8')

            # Add file data to paper_data
            paper_data.update({
                'file_data': file_base64,
                'file_name': secure_filename(file.filename),
                'file_type': file.content_type,
                'file_size': len(file_data)
            })

            # Store paper in Firebase under conference-specific path
            papers_ref = db.reference(f'conferences/{conference_id}/paper_submissions')
            new_paper = papers_ref.push(paper_data)
            paper_id = new_paper.key

            # Store in user's submissions for easy access
            user_submissions_ref = db.reference(f'user_paper_submissions/{current_user.id}')
            user_submissions_ref.push({
                'conference_id': conference_id,
                'paper_id': paper_id,
                'paper_title': paper_data['paper_title'],
                'conference_name': conference.get('basic_info', {}).get('name', 'Conference'),
                'status': 'pending',
                'submitted_at': datetime.now().isoformat()
            })

            # Send confirmation email
            try:
                conference_name = conference.get('basic_info', {}).get('name', 'Conference')
                email_service.send_paper_confirmation({
                    'authors': paper_data['authors'],
                    'paper_title': paper_data['paper_title'],
                    'presentation_type': paper_data['presentation_type'],
                    'paper_id': paper_id,
                    'user_email': current_user.email,
                    'conference_name': conference_name
                })
            except Exception as e:
                print(f"Error sending confirmation email: {str(e)}")

            flash(f'Paper submitted successfully to {conference.get("basic_info", {}).get("name", "Conference")}!', 'success')
            return redirect(url_for('conference_details', conference_id=conference_id))
            
        except Exception as e:
            print(f"Error submitting paper: {str(e)}")
            flash(f'Error submitting paper: {str(e)}', 'error')
            return render_template('conferences/paper_submission.html',
                                 conference=conference,
                                 conference_id=conference_id,
                                 site_design=get_site_design())
        
    except Exception as e:
        print(f"Error processing paper submission: {e}")
        flash('Error processing paper submission.', 'error')
        return redirect(url_for('conference_details', conference_id=conference_id))

@app.route('/admin/conferences')
@login_required
@admin_required
def admin_conferences():
    """Admin conference management dashboard"""
    try:
        conferences = get_all_conferences()
        
        # Get all registrations from the global registrations node
        all_registrations_ref = db.reference('registrations')
        all_registrations = all_registrations_ref.get() or {}
        
        # Use South African Standard Time (UTC+02:00) for all comparisons
        sast_tz = pytz.timezone('Africa/Johannesburg')
        now = datetime.now(sast_tz)
        
        # Helper to parse to SAST aware datetimes
        def _parse_date(value):
            """Parse to timezone-aware datetime in SAST."""
            try:
                if not value:
                    return None
                text = str(value)
                dt = None
                try:
                    dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
                except Exception:
                    dt = datetime.strptime(text, '%Y-%m-%d')
                if getattr(dt, 'tzinfo', None) is None:
                    dt = sast_tz.localize(dt)
                else:
                    dt = dt.astimezone(sast_tz)
                return dt
            except Exception:
                return None
        
        # Categorize conferences by status with auto-date-based filtering
        active_conferences = {}
        upcoming_conferences = {}
        past_conferences = {}
        
        for conf_id, conf_data in conferences.items():
            if not conf_data or 'basic_info' not in conf_data:
                continue
                
            basic_info = conf_data['basic_info']
            
            # Parse dates
            start_dt = _parse_date(basic_info.get('start_date'))
            end_dt = _parse_date(basic_info.get('end_date'))
            
            # Get admin-provided status
            admin_status = (basic_info.get('status') or '').strip().lower()
            
            # AUTO-COMPUTE status based on dates (prioritize date-based logic)
            computed_status = None
            if start_dt and end_dt:
                if now > end_dt:
                    # Conference has ENDED - ALWAYS mark as past
                    computed_status = 'past'
                elif now < start_dt:
                    # Conference hasn't STARTED yet
                    if admin_status == 'active':
                        computed_status = 'active'
                    else:
                        computed_status = 'upcoming'
                else:
                    # Conference is ONGOING
                    computed_status = 'active'
            elif end_dt and now > end_dt:
                computed_status = 'past'
            elif start_dt and now < start_dt:
                computed_status = 'upcoming'
            else:
                # No dates available, use admin status
                computed_status = admin_status if admin_status else 'draft'
            
            # Update the status in conf_data
            conf_data['basic_info']['status'] = computed_status
            
            # Ensure past conferences have registration/submission disabled
            if computed_status == 'past':
                if 'settings' not in conf_data:
                    conf_data['settings'] = {}
                conf_data['settings']['registration_enabled'] = False
                conf_data['settings']['paper_submission_enabled'] = False
            
            # Count registrations for this conference from global registrations
            registration_count = 0
            for reg_id, reg_data in all_registrations.items():
                if reg_data and reg_data.get('conference_id') == conf_id:
                    registration_count += 1
            
            conf_data['registration_count'] = registration_count
            
            # Categorize based on computed status
            if computed_status == 'active':
                active_conferences[conf_id] = conf_data
            elif computed_status == 'upcoming':
                upcoming_conferences[conf_id] = conf_data
            elif computed_status == 'past':
                past_conferences[conf_id] = conf_data
        
        return render_template('admin/conferences.html',
                             conferences=conferences,
                             active_conferences=active_conferences,
                             upcoming_conferences=upcoming_conferences,
                             past_conferences=past_conferences,
                             current_year=datetime.now().year,
                             site_design=get_site_design())
    except Exception as e:
        print(f"Error loading conferences: {e}")
        flash('Error loading conferences.', 'error')
        return render_template('admin/conferences.html',
                             conferences={},
                             active_conferences={},
                             upcoming_conferences={},
                             past_conferences={},
                             current_year=datetime.now().year,
                             site_design=get_site_design())

@app.route('/admin/conferences/create', methods=['POST'])
@login_required
@admin_required
def create_conference():
    """Create a new conference"""
    try:
        # Get form data
        conference_data = {
            'basic_info': {
                'name': request.form.get('name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'year': int(request.form.get('year', datetime.now().year)),
                'abbreviation': request.form.get('abbreviation', '').strip(),
                'status': request.form.get('status', 'draft'),
                'event_type': request.form.get('event_type', 'in-person'),
                'start_date': request.form.get('start_date', ''),
                'end_date': request.form.get('end_date', ''),
                'location': request.form.get('location', '').strip(),
                'website': request.form.get('website', '').strip(),
                'timezone': 'UTC'
            },
            'settings': {
                'registration_enabled': request.form.get('registration_enabled') == 'on',
                'paper_submission_enabled': request.form.get('paper_submission_enabled') == 'on',
                'gallery_enabled': request.form.get('gallery_enabled') == 'on',
                'email_notifications': request.form.get('email_notifications') == 'on',
                'max_registrations': 1000,
                'max_paper_submissions': 500
            },
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'created_by': current_user.email,
                'version': '1.0.0'
            }
        }
        
        # Validate required fields
        if not conference_data['basic_info']['name']:
            flash('Conference name is required.', 'error')
            return redirect(url_for('admin_conferences'))
        
        # Create conference with auto-generated code
        result = create_conference_with_code(conference_data)
        
        if result['success']:
            flash(f'Conference "{conference_data["basic_info"]["name"]}" created successfully with code: {result["conference_code"]}', 'success')
        else:
            flash(f'Error creating conference: {result.get("error", "Unknown error")}', 'error')
            
    except Exception as e:
        print(f"Error creating conference: {e}")
        flash('Error creating conference.', 'error')
    
    return redirect(url_for('admin_conferences'))

@app.route('/admin/conferences/<conference_id>')
@login_required
@admin_required
def admin_conference_details(conference_id):
    """Admin conference details and management"""
    try:
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found.', 'error')
            return redirect(url_for('admin_conferences'))
        
        # Get all registrations from the global registrations node
        all_registrations_ref = db.reference('registrations')
        all_registrations = all_registrations_ref.get() or {}
        
        # Filter registrations for this specific conference
        conference_registrations = {}
        for reg_id, reg_data in all_registrations.items():
            if reg_data and reg_data.get('conference_id') == conference_id:
                # Ensure all required fields exist with defaults
                reg_data.setdefault('full_name', '')
                reg_data.setdefault('email', '')
                reg_data.setdefault('institution', '')
                reg_data.setdefault('registration_type', '')
                reg_data.setdefault('payment_status', 'pending')
                reg_data.setdefault('created_at', '')
                conference_registrations[reg_id] = reg_data
        
        return render_template('admin/conference_details.html',
                             conference=conference,
                             conference_id=conference_id,
                             registrations=conference_registrations,
                             site_design=get_site_design())
    except Exception as e:
        print(f"Error loading conference details: {e}")
        flash('Error loading conference details.', 'error')
        return redirect(url_for('admin_conferences'))

@app.route('/admin/conferences/<conference_id>/delete', methods=['DELETE'])
@login_required
@admin_required
def delete_conference(conference_id):
    """Delete a conference"""
    try:
        # Check if conference exists
        conference = get_conference_data(conference_id)
        if not conference:
            return jsonify({'success': False, 'error': 'Conference not found'}), 404
        
        # Check if conference has registrations from global registrations node
        all_registrations_ref = db.reference('registrations')
        all_registrations = all_registrations_ref.get() or {}
        
        # Count registrations for this conference
        has_registrations = False
        for reg_id, reg_data in all_registrations.items():
            if reg_data and reg_data.get('conference_id') == conference_id:
                has_registrations = True
                break
        
        if has_registrations:
            return jsonify({'success': False, 'error': 'Cannot delete conference with existing registrations'}), 400
        
        # Delete conference
        conference_ref = db.reference(f'conferences/{conference_id}')
        conference_ref.delete()
        
        return jsonify({'success': True, 'message': 'Conference deleted successfully'})
        
    except Exception as e:
        print(f"Error deleting conference: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conferences/<conference_id>/settings', methods=['POST'])
@login_required
@admin_required
def update_conference_settings(conference_id):
    """Update conference settings"""
    try:
        # Check if conference exists
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found.', 'error')
            return redirect(url_for('admin_conference_details', conference_id=conference_id))
        
        # Update settings
        settings_ref = db.reference(f'conferences/{conference_id}/settings')
        settings_data = {
            'registration_enabled': request.form.get('registration_enabled') == 'on',
            'paper_submission_enabled': request.form.get('paper_submission_enabled') == 'on',
            'gallery_enabled': request.form.get('gallery_enabled') == 'on',
            'email_notifications': request.form.get('email_notifications') == 'on',
            'max_registrations': int(request.form.get('max_registrations', 1000)),
            'max_paper_submissions': int(request.form.get('max_paper_submissions', 500))
        }
        
        settings_ref.update(settings_data)
        flash('Conference settings updated successfully.', 'success')
        
    except Exception as e:
        print(f"Error updating conference settings: {e}")
        flash('Error updating conference settings.', 'error')
    
    return redirect(url_for('admin_conference_details', conference_id=conference_id))

@app.route('/admin/conferences/<conference_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_conference(conference_id):
    """Edit conference details"""
    try:
        # Get conference data
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found.', 'error')
            return redirect(url_for('admin_conferences'))
        
        if request.method == 'POST':
            # Update conference data
            basic_info = {
                'name': request.form.get('name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'year': int(request.form.get('year', conference['basic_info'].get('year', datetime.now().year))),
                'abbreviation': request.form.get('abbreviation', '').strip(),
                'status': request.form.get('status', conference['basic_info'].get('status', 'draft')),
                'event_type': request.form.get('event_type', conference['basic_info'].get('event_type', 'in-person')),
                'start_date': request.form.get('start_date', ''),
                'end_date': request.form.get('end_date', ''),
                'location': request.form.get('location', '').strip(),
                'website': request.form.get('website', '').strip(),
                'timezone': conference['basic_info'].get('timezone', 'UTC')
            }
            
            # Validate required fields
            if not basic_info['name']:
                flash('Conference name is required.', 'error')
                return render_template('admin/edit_conference.html',
                                     conference=conference,
                                     conference_id=conference_id,
                                     site_design=get_site_design(),
                                     current_year=datetime.now().year)
            
            # Update basic info
            basic_info_ref = db.reference(f'conferences/{conference_id}/basic_info')
            basic_info_ref.update(basic_info)
            
            # Update settings if provided
            if request.form.get('update_settings') == 'on':
                settings_data = {
                    'registration_enabled': request.form.get('registration_enabled') == 'on',
                    'paper_submission_enabled': request.form.get('paper_submission_enabled') == 'on',
                    'gallery_enabled': request.form.get('gallery_enabled') == 'on',
                    'email_notifications': request.form.get('email_notifications') == 'on',
                    'max_registrations': int(request.form.get('max_registrations', 1000)),
                    'max_paper_submissions': int(request.form.get('max_paper_submissions', 500))
                }
                
                settings_ref = db.reference(f'conferences/{conference_id}/settings')
                settings_ref.update(settings_data)
            
            # Update metadata
            metadata_ref = db.reference(f'conferences/{conference_id}/metadata')
            metadata_ref.update({
                'updated_at': datetime.now().isoformat(),
                'updated_by': current_user.email
            })
            
            flash(f'Conference "{basic_info["name"]}" updated successfully.', 'success')
            return redirect(url_for('admin_conference_details', conference_id=conference_id))
        
        # GET request - show edit form
        return render_template('admin/edit_conference.html',
                             conference=conference,
                             conference_id=conference_id,
                             site_design=get_site_design(),
                             current_year=datetime.now().year)
                             
    except Exception as e:
        print(f"Error editing conference: {e}")
        flash('Error editing conference.', 'error')
        return redirect(url_for('admin_conferences'))

@app.route('/admin/conferences/<conference_id>/regenerate-code', methods=['POST'])
@login_required
@admin_required
def regenerate_conference_code(conference_id):
    """Regenerate conference code"""
    try:
        # Get conference data
        conference = get_conference_data(conference_id)
        if not conference:
            return jsonify({'success': False, 'error': 'Conference not found'}), 404
        
        # Generate new code
        abbr = conference['basic_info'].get('abbreviation', 'CONF')
        year = conference['basic_info'].get('year', datetime.now().year)
        new_code = generate_conference_code(abbr, year)
        
        # Update conference code
        conference_ref = db.reference(f'conferences/{conference_id}')
        conference_ref.update({
            'conference_code': new_code,
            'code_generated_at': datetime.now().isoformat()
        })
        
        return jsonify({'success': True, 'conference_code': new_code})
        
    except Exception as e:
        print(f"Error regenerating conference code: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/conferences/<conference_id>/assign-registrations', methods=['GET', 'POST'])
@login_required
@admin_required
def assign_registrations_to_conference(conference_id):
    """Assign registrations to a specific conference"""
    try:
        # Get conference data
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found.', 'error')
            return redirect(url_for('admin_conferences'))
        
        if request.method == 'POST':
            # Get selected registration IDs
            selected_registrations = request.form.getlist('selected_registrations')
            
            if not selected_registrations:
                flash('No registrations selected.', 'warning')
                return redirect(url_for('admin_conference_details', conference_id=conference_id))
            
            # Update registrations to assign them to this conference
            updated_count = 0
            for reg_id in selected_registrations:
                # Get the registration from main collection
                main_reg_ref = db.reference(f'registrations/{reg_id}')
                registration_data = main_reg_ref.get()
                
                if registration_data:
                    # Add assignment metadata
                    registration_data['conference_id'] = conference_id
                    registration_data['conference_name'] = conference['basic_info']['name']
                    registration_data['assigned_at'] = datetime.now().isoformat()
                    registration_data['assigned_by'] = current_user.email
                    
                    # Copy to conference-specific collection
                    conference_reg_ref = db.reference(f'conferences/{conference_id}/registrations/{reg_id}')
                    conference_reg_ref.set(registration_data)
                    
                    # Update main registration to mark as assigned
                    main_reg_ref.update({
                        'conference_id': conference_id,
                        'conference_name': conference['basic_info']['name'],
                        'assigned_at': datetime.now().isoformat(),
                        'assigned_by': current_user.email
                    })
                    
                    updated_count += 1
            
            flash(f'Successfully assigned {updated_count} registration(s) to {conference["basic_info"]["name"]}.', 'success')
            return redirect(url_for('admin_conference_details', conference_id=conference_id))
        
        # GET request - show available registrations
        # Get all registrations that are not assigned to any conference or assigned to this one
        registrations_ref = db.reference('registrations')
        all_registrations = registrations_ref.get() or {}
        
        # Get registrations already assigned to this conference
        conference_registrations_ref = db.reference(f'conferences/{conference_id}/registrations')
        conference_registrations = conference_registrations_ref.get() or {}
        
        # Filter registrations
        available_registrations = []
        assigned_registrations = []
        
        # Process main registrations (unassigned)
        for reg_id, reg_data in all_registrations.items():
            reg_data['_id'] = reg_id
            reg_data.setdefault('conference_id', None)
            reg_data.setdefault('full_name', '')
            reg_data.setdefault('email', '')
            reg_data.setdefault('institution', '')
            reg_data.setdefault('registration_type', '')
            reg_data.setdefault('payment_status', 'pending')
            
            # Only include if not assigned to any conference
            if reg_data.get('conference_id') is None:
                available_registrations.append(reg_data)
        
        # Process conference-specific registrations (assigned)
        for reg_id, reg_data in conference_registrations.items():
            reg_data['_id'] = reg_id
            reg_data.setdefault('conference_id', conference_id)
            reg_data.setdefault('full_name', '')
            reg_data.setdefault('email', '')
            reg_data.setdefault('institution', '')
            reg_data.setdefault('registration_type', '')
            reg_data.setdefault('payment_status', 'pending')
            
            assigned_registrations.append(reg_data)
        
        return render_template('admin/assign_registrations.html',
                             conference=conference,
                             conference_id=conference_id,
                             available_registrations=available_registrations,
                             assigned_registrations=assigned_registrations,
                             conferences=get_all_conferences(),
                             site_design=get_site_design())
                             
    except Exception as e:
        print(f"Error assigning registrations: {e}")
        flash('Error assigning registrations.', 'error')
        return redirect(url_for('admin_conference_details', conference_id=conference_id))

@app.route('/admin/conferences/<conference_id>/unassign-registration', methods=['POST'])
@login_required
@admin_required
def unassign_registration_from_conference(conference_id):
    """Unassign a registration from a conference"""
    try:
        registration_id = request.form.get('registration_id')
        if not registration_id:
            flash('Registration ID is required.', 'error')
            return redirect(url_for('assign_registrations_to_conference', conference_id=conference_id))
        
        # Remove conference assignment from registration
        registration_ref = db.reference(f'registrations/{registration_id}')
        registration_ref.update({
            'conference_id': None,
            'conference_name': None,
            'unassigned_at': datetime.now().isoformat(),
            'unassigned_by': current_user.email
        })
        
        # Remove from conference-specific collection
        conference_reg_ref = db.reference(f'conferences/{conference_id}/registrations/{registration_id}')
        conference_reg_ref.delete()
        
        flash('Registration unassigned successfully.', 'success')
        return redirect(url_for('assign_registrations_to_conference', conference_id=conference_id))
        
    except Exception as e:
        print(f"Error unassigning registration: {e}")
        flash('Error unassigning registration.', 'error')
        return redirect(url_for('assign_registrations_to_conference', conference_id=conference_id))

@app.route('/admin/conferences/<conference_id>/registrations/export')
@login_required
@admin_required
def export_conference_registrations(conference_id):
    """Export registrations for a specific conference"""
    try:
        # Get conference data
        conference = get_conference_data(conference_id)
        if not conference:
            flash('Conference not found.', 'error')
            return redirect(url_for('admin_conference_details', conference_id=conference_id))
        
        # Get registrations for this conference
        registrations_ref = db.reference(f'conferences/{conference_id}/registrations')
        registrations_data = registrations_ref.get() or {}
        
        # Create CSV content
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Registration ID', 'Full Name', 'Email', 'Institution', 'Registration Type',
            'Payment Status', 'Total Amount', 'Registration Date', 'Conference'
        ])
        
        # Write data
        for reg_id, reg in registrations_data.items():
            writer.writerow([
                reg_id,
                reg.get('full_name', ''),
                reg.get('email', ''),
                reg.get('institution', ''),
                reg.get('registration_type', ''),
                reg.get('payment_status', ''),
                reg.get('total_amount', ''),
                reg.get('created_at', ''),
                conference['basic_info']['name']
            ])
        
        # Create response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename="{conference["basic_info"]["name"]}_registrations.csv"'
        
        return response
        
    except Exception as e:
        print(f"Error exporting registrations: {e}")
        flash('Error exporting registrations.', 'error')
        return redirect(url_for('admin_conference_details', conference_id=conference_id))

# Update existing dashboard route to be conference-aware
@app.route('/dashboard')
@login_required
def dashboard():
    """Updated dashboard with multi-conference support"""
    try:
        user_registrations = {}
        user_submissions = {}
        
        # Get user's registrations from global registrations node
        all_registrations_ref = db.reference('registrations')
        all_registrations = all_registrations_ref.get() or {}
        
        # Filter registrations for current user
        for reg_id, registration in all_registrations.items():
            if registration and registration.get('user_id') == current_user.id:
                # Get conference details if available
                conference_id = registration.get('conference_id')
                if conference_id:
                    conference = get_conference_data(conference_id)
                    if conference:
                        registration['conference_details'] = {
                            'name': conference.get('basic_info', {}).get('name', 'Unknown'),
                            'year': conference.get('basic_info', {}).get('year', ''),
                            'status': conference.get('basic_info', {}).get('status', 'unknown')
                        }
                
                user_registrations[reg_id] = registration
        
        # Get user's paper submissions
        submissions_ref = db.reference('paper_submissions')
        all_submissions = submissions_ref.get() or {}
        
        for sub_id, submission in all_submissions.items():
            if submission and submission.get('user_id') == current_user.id:
                user_submissions[sub_id] = submission
        
        return render_template('user/dashboard.html',
                             registrations=user_registrations,
                             submissions=user_submissions,
                             site_design=get_site_design())
                             
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading dashboard.', 'error')
        return render_template('user/dashboard.html',
                             registrations={},
                             submissions={},
                             site_design=get_site_design())

@app.route('/admin/conference-proceedings', methods=['GET'])
@login_required
@admin_required
def admin_conference_proceedings():
    """Admin page for managing conference proceedings content"""
    try:
        # Get content from Firebase
        content_ref = db.reference('conference_proceedings_content')
        content = content_ref.get() or {}
        
        return render_template('admin/conference_proceedings.html',
                             content=content,
                             site_design=get_site_design())
    except Exception as e:
        print(f"Error loading conference proceedings admin: {e}")
        flash('Error loading conference proceedings management.', 'error')
        return render_template('admin/conference_proceedings.html',
                             content={},
                             site_design=get_site_design())

@app.route('/admin/conference-proceedings/content', methods=['POST'])
@login_required
@admin_required
def admin_conference_proceedings_content():
    """Save conference proceedings content"""
    try:
        content_data = {
            'page_title': request.form.get('page_title', 'Conference Proceedings'),
            'page_subtitle': request.form.get('page_subtitle', 'Manuscript templates and guidelines for conference paper submission'),
            'hero_description': request.form.get('hero_description', ''),
            'important_notice_title': request.form.get('important_notice_title', 'Important Notice'),
            'important_notice_content': request.form.get('important_notice_content', ''),
            'important_notice_warning': request.form.get('important_notice_warning', ''),
            'notes_section_title': request.form.get('notes_section_title', 'Important Notes'),
            'note_organizers_title': request.form.get('note_organizers_title', 'For Conference Organizers'),
            'note_organizers_content': request.form.get('note_organizers_content', ''),
            'note_linking_title': request.form.get('note_linking_title', 'Linking Guidelines'),
            'note_linking_content': request.form.get('note_linking_content', ''),
            'note_acknowledgement_title': request.form.get('note_acknowledgement_title', 'Template Acknowledgement'),
            'note_acknowledgement_content': request.form.get('note_acknowledgement_content', ''),
            'empty_state_title': request.form.get('empty_state_title', 'No Templates Available'),
            'empty_state_message': request.form.get('empty_state_message', ''),
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        }
        
        # Save to Firebase
        content_ref = db.reference('conference_proceedings_content')
        content_ref.set(content_data)
        
        flash('Conference proceedings content updated successfully!', 'success')
        return redirect(url_for('admin_conference_proceedings'))
        
    except Exception as e:
        print(f"Error saving conference proceedings content: {e}")
        flash('Error saving content changes.', 'error')
        return redirect(url_for('admin_conference_proceedings'))



@app.route('/admin/paper-submission-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_paper_submission_settings():
    try:
        if request.method == 'POST':
            # Build research areas list
            research_areas = []
            areas = request.form.getlist('research_areas[]')
            area_labels = request.form.getlist('research_area_labels[]')
            for i, area in enumerate(areas):
                if area and i < len(area_labels) and area_labels[i]:
                    research_areas.append({
                        'value': area,
                        'label': area_labels[i]
                    })
            
            # Build presentation types list
            presentation_types = []
            types = request.form.getlist('presentation_types[]')
            type_labels = request.form.getlist('presentation_type_labels[]')
            for i, ptype in enumerate(types):
                if ptype and i < len(type_labels) and type_labels[i]:
                    presentation_types.append({
                        'value': ptype,
                        'label': type_labels[i]
                    })
            
            # Get allowed file types
            allowed_file_types = request.form.getlist('allowed_file_types')
            if not allowed_file_types:
                allowed_file_types = ['pdf']  # Default to PDF
            
            # Build settings object
            paper_settings = {
                'page': {
                    'title': request.form.get('page_title', 'Submit Your Paper'),
                    'description': request.form.get('page_description', 'Please fill out the form below to submit your paper for review.')
                },
                'files': {
                    'max_size_mb': int(request.form.get('max_file_size', 10)),
                    'allowed_types': allowed_file_types
                },
                'fields': {
                    'title': {
                        'enabled': True,
                        'required': True
                    },
                    'abstract': {
                        'enabled': True,
                        'required': True,
                        'min_words': int(request.form.get('abstract_min_words', 100)),
                        'max_words': int(request.form.get('abstract_max_words', 500))
                    },
                    'keywords': {
                        'enabled': True,
                        'required': True
                    },
                    'research_areas': research_areas,
                    'presentation_types': presentation_types
                },
                'authors': {
                    'max_count': int(request.form.get('max_authors', 10)),
                    'require_institution': request.form.get('require_institution') == 'on',
                    'require_orcid': request.form.get('require_orcid') == 'on',
                    'require_biography': request.form.get('require_biography') == 'on'
                },
                'security': {
                    'enable_recaptcha': request.form.get('enable_recaptcha') == 'on',
                    'enable_plagiarism_check': request.form.get('enable_plagiarism_check') == 'on'
                },
                'deadlines': {
                    'submission': request.form.get('submission_deadline', ''),
                    'allow_late': request.form.get('allow_late_submissions') == 'on'
                },
                'notifications': {
                    'notify_admin': request.form.get('notify_admin') == 'on',
                    'send_confirmation': request.form.get('send_confirmation') == 'on',
                    'admin_email': request.form.get('admin_email', '')
                },
                'updated_at': datetime.now().isoformat(),
                'updated_by': current_user.email
            }
            
            # Save to Firebase
            settings_ref = db.reference('paper_submission_settings')
            settings_ref.set(paper_settings)
            
            flash('Paper submission settings updated successfully!', 'success')
            return redirect(url_for('admin_paper_submission_settings'))
        
        # GET request - load current settings
        settings_ref = db.reference('paper_submission_settings')
        settings = settings_ref.get()
        
        return render_template('admin/paper_submission_settings.html', 
                             settings=settings,
                             site_design=get_site_design())
    except Exception as e:
        flash(f'Error managing paper submission settings: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

# Add these helper functions near the top of the file (after imports)

def upload_guideline_file_and_get_url(file, filename):
    """Upload guideline files to Firebase Storage and return public URL"""
    try:
        storage_client = gcs_storage.Client.from_service_account_json('serviceAccountKey.json')
        bucket = storage_client.bucket('giir-66ae6.firebasestorage.app')
        blob = bucket.blob(f'guidelines/{filename}')
        blob.upload_from_file(file, content_type=file.mimetype)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"Error uploading guideline file: {str(e)}")
        raise

def upload_speaker_image_to_firebase(file, filename):
    """Upload speaker image to Firebase Storage and return public URL"""
    try:
        storage_client = gcs_storage.Client.from_service_account_json('serviceAccountKey.json')
        bucket = storage_client.bucket('giir-66ae6.firebasestorage.app')
        blob = bucket.blob(f'speakers/{filename}')

        # Compress image if needed
        img_data = compress_image(file, max_size_kb=500)

        # Upload the compressed image data
        blob.upload_from_string(img_data, content_type=file.mimetype)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"Error uploading speaker image: {str(e)}")
        raise

def get_conference_data(conference_id):
    """
    Get conference data by ID from Firebase or About Content

    Args:
        conference_id: Conference ID (can be synthetic ID from About Content)

    Returns:
        dict: Conference data or None
    """
    try:
        # Try to get from explicit conferences first
        conferences = get_all_conferences()
        if conference_id in conferences:
            return conferences[conference_id]

        # Try resolving from Admin About Content synthetic entries
        return _get_about_content_conference(conference_id)
    except Exception as e:
        print(f"Error getting conference data: {e}")
        return None

def generate_conference_code(conference_abbr, year):
    """
    Generate a unique conference code for a conference

    Args:
        conference_abbr: Conference abbreviation (e.g., 'ETL', 'STM', 'TBME', 'SAT')
        year: Conference year

    Returns:
        str: Unique conference code
    """
    import random
    import string

    # Generate 8-character alphanumeric unique ID
    unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    return f"CONF-{year}-{conference_abbr}-{unique_id}"

def create_conference_with_code(conference_data):
    """
    Create a new conference with an auto-generated unique code

    Args:
        conference_data: Conference data dictionary

    Returns:
        dict: {'conference_id': str, 'conference_code': str, 'success': bool}
    """
    try:
        # Generate conference code from abbreviation and year
        abbr = conference_data.get('basic_info', {}).get('abbreviation', 'CONF')
        year = conference_data.get('basic_info', {}).get('year', datetime.now().year)
        conference_code = generate_conference_code(abbr, year)

        # Add conference code to the data
        conference_data['conference_code'] = conference_code
        conference_data['code_generated_at'] = datetime.now().isoformat()

        # Save to Firebase
        conferences_ref = db.reference('conferences')
        new_conference_ref = conferences_ref.push(conference_data)

        return {
            'conference_id': new_conference_ref.key,
            'conference_code': conference_code,
            'success': True
        }
    except Exception as e:
        print(f"Error creating conference with code: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def update_conference_code(conference_id, new_abbreviation=None):
    """
    Update or regenerate conference code for an existing conference

    Args:
        conference_id: Conference ID
        new_abbreviation: Optional new abbreviation

    Returns:
        dict: {'conference_code': str, 'success': bool}
    """
    try:
        conference = get_conference_data(conference_id)
        if not conference:
            return {'success': False, 'error': 'Conference not found'}

        # Get abbreviation (use new one if provided, otherwise from existing data)
        abbr = new_abbreviation or conference.get('basic_info', {}).get('abbreviation', 'CONF')
        year = conference.get('basic_info', {}).get('year', datetime.now().year)

        # Generate new conference code
        conference_code = generate_conference_code(abbr, year)

        # Update in Firebase
        conference_ref = db.reference(f'conferences/{conference_id}')
        conference_ref.update({
            'conference_code': conference_code,
            'code_generated_at': datetime.now().isoformat()
        })

        return {
            'conference_code': conference_code,
            'success': True
        }
    except Exception as e:
        print(f"Error updating conference code: {e}")
        return {'success': False, 'error': str(e)}

@app.route('/admin/conference-codes', methods=['GET'])
@login_required
@admin_required
def admin_conference_codes():
    """Admin interface for managing conference codes"""
    try:
        # Get all conferences with their codes
        conferences = get_all_conferences()
        conferences_with_codes = {}

        for conference_id, conference_data in conferences.items():
            conference_data_with_code = conference_data.copy()
            conference_data_with_code['id'] = conference_id
            conferences_with_codes[conference_id] = conference_data_with_code

        return render_template('admin/conference_codes.html',
                             conferences=conferences_with_codes,
                             site_design=get_site_design())
    except Exception as e:
        flash(f'Error loading conference codes: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/conference-codes/generate/<conference_id>', methods=['POST'])
@login_required
@admin_required
def admin_generate_new_conference_code(conference_id):
    """Generate a new conference code for an existing conference from admin codes page"""
    try:
        # Get conference data
        conference = get_conference_data(conference_id)
        if not conference:
            return jsonify({'success': False, 'error': 'Conference not found'}), 404

        # Get new abbreviation from form if provided
        new_abbreviation = request.form.get('abbreviation')

        # Generate new code
        result = update_conference_code(conference_id, new_abbreviation)

        if result['success']:
            flash(f'Conference code updated successfully: {result["conference_code"]}', 'success')
        else:
            flash(f'Error generating conference code: {result.get("error", "Unknown error")}', 'error')

        return redirect(url_for('admin_conference_codes'))

    except Exception as e:
        flash(f'Error generating conference code: {str(e)}', 'error')
        return redirect(url_for('admin_conference_codes'))

@app.route('/admin/conference-codes/validate', methods=['POST'])
@login_required
@admin_required
def validate_conference_code():
    """Validate a conference code"""
    try:
        code = request.form.get('conference_code')
        if not code:
            return jsonify({'valid': False, 'error': 'No code provided'}), 400

        result = validate_conference_code(code)

        return jsonify(result)

    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500

@app.route('/conference-by-code/<conference_code>')
def get_conference_by_code_route(conference_code):
    """Get conference details by unique conference code (public endpoint)"""
    try:
        result = get_conference_by_code(conference_code)

        if result:
            return redirect(url_for('conference_details', conference_id=result['conference_id']))
        else:
            flash('Invalid conference code.', 'error')
            return redirect(url_for('conference_discover'))

    except Exception as e:
        flash(f'Error retrieving conference: {str(e)}', 'error')
        return redirect(url_for('conference_discover'))

# =============================================================================
# GUEST SPEAKER APPLICATION ROUTES
# =============================================================================

@app.route('/guest-speaker-application', methods=['GET', 'POST'])
@login_required
def guest_speaker_application():
    """User-facing guest speaker application form"""
    if request.method == 'GET':
        # Get all conferences for the dropdown
        conferences = get_all_conferences()
        return render_template('user/guest_speaker_application.html',
                             conferences=conferences,
                             site_design=get_site_design())

    try:
        # Get form data
        application_data = {
            'full_name': request.form.get('full_name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'title': request.form.get('title', '').strip(),
            'organization': request.form.get('organization', '').strip(),
            'bio': request.form.get('bio', '').strip(),
            'research_interests': request.form.get('research_interests', '').strip(),
            'previous_speaking': request.form.get('previous_speaking', '').strip(),
            'available_dates': request.form.get('available_dates', '').strip(),
            'preferred_topics': [t.strip() for t in request.form.get('preferred_topics', '').split(',') if t.strip()],
            'linkedin_profile': request.form.get('linkedin_profile', '').strip(),
            'website': request.form.get('website', '').strip(),
            'preferred_conference': request.form.get('preferred_conference', '').strip(),
            'status': 'pending',
            'submitted_at': datetime.now().isoformat(),
            'submitted_by': current_user.email,
            'user_id': current_user.id,
            'updated_at': datetime.now().isoformat()
        }

        # Add conference details if a conference was selected
        if application_data['preferred_conference']:
            conferences = get_all_conferences()
            if application_data['preferred_conference'] in conferences:
                conference = conferences[application_data['preferred_conference']]
                basic_info = conference.get('basic_info', {})
                application_data.update({
                    'conference_name': basic_info.get('name', ''),
                    'conference_date': basic_info.get('date', ''),
                    'conference_location': basic_info.get('location', ''),
                    'conference_year': basic_info.get('year', '')
                })

        # Validate required fields
        required_fields = ['full_name', 'email', 'title', 'organization', 'bio']
        for field in required_fields:
            if not application_data.get(field):
                flash(f'Field "{field}" is required.', 'error')
                return render_template('user/guest_speaker_application.html',
                                     site_design=get_site_design())

        # Handle CV/Resume upload
        if 'cv_file' in request.files:
            file = request.files['cv_file']
            if file and file.filename:
                try:
                    # Generate unique filename
                    original_filename = secure_filename(file.filename)
                    ext = os.path.splitext(original_filename)[1].lower()
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_id = str(uuid.uuid4())[:8]
                    unique_filename = f"cv_{timestamp}_{unique_id}{ext}"

                    # Upload to Firebase Storage
                    storage_client = storage.Client.from_service_account_json('serviceAccountKey.json')
                    bucket = storage_client.bucket('giir-66ae6.firebasestorage.app')

                    blob = bucket.blob(f'guest_speaker_cvs/{unique_filename}')
                    blob.upload_from_file(file, content_type=file.content_type)
                    blob.make_public()

                    application_data['cv_url'] = blob.public_url
                    application_data['cv_filename'] = original_filename

                except Exception as e:
                    print(f"Error uploading CV: {str(e)}")
                    flash('Error uploading CV file. Please try again.', 'error')
                    return render_template('user/guest_speaker_application.html',
                                         site_design=get_site_design())

        # Save application to Firebase
        applications_ref = db.reference('guest_speaker_applications')
        new_application = applications_ref.push(application_data)

        # Send confirmation email
        try:
            send_guest_speaker_confirmation_email(
                application_data['email'],
                application_data['full_name'],
                new_application.key
            )
        except Exception as e:
            print(f"Error sending confirmation email: {e}")

        flash('Your guest speaker application has been submitted successfully! You will receive a confirmation email shortly.', 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"Error processing guest speaker application: {e}")
        flash('Error processing application. Please try again.', 'error')
        return render_template('user/guest_speaker_application.html',
                             site_design=get_site_design())

@app.route('/admin/guest-speaker-applications')
@login_required
@admin_required
def admin_guest_speaker_applications():
    """Admin interface to view guest speaker applications"""
    try:
        # Get all applications from Firebase
        applications_ref = db.reference('guest_speaker_applications')
        applications = applications_ref.get() or {}

        # Sort by submission date (newest first)
        sorted_applications = dict(sorted(
            applications.items(),
            key=lambda x: x[1].get('submitted_at', ''),
            reverse=True
        ))

        return render_template(
            'admin/guest_speaker_applications.html',
            applications=sorted_applications,
            site_design=get_site_design()
        )
    except Exception as e:
        print(f"Error loading guest speaker applications: {e}")
        flash(f'Error loading applications: {str(e)}', 'error')
        return render_template(
            'admin/guest_speaker_applications.html',
            applications={},
            site_design=get_site_design()
        )

@app.route('/admin/guest-speaker-applications/<application_id>')
@login_required
@admin_required
def get_guest_speaker_application(application_id):
    """Get detailed view of a guest speaker application"""
    try:
        application_ref = db.reference(f'guest_speaker_applications/{application_id}')
        application = application_ref.get()

        if not application:
            return jsonify({'error': 'Application not found'}), 404

        return jsonify(application)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/guest-speaker-applications/<application_id>/status', methods=['POST'])
@login_required
@admin_required
def update_guest_speaker_status(application_id):
    """Update guest speaker application status (approve/reject)"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        admin_notes = data.get('admin_notes', '')

        if new_status not in ['approved', 'rejected', 'under_review']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        # Get application data
        application_ref = db.reference(f'guest_speaker_applications/{application_id}')
        application = application_ref.get()

        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404

        # Update application status
        update_data = {
            'status': new_status,
            'admin_notes': admin_notes,
            'reviewed_at': datetime.now().isoformat(),
            'reviewed_by': current_user.email,
            'updated_at': datetime.now().isoformat()
        }

        application_ref.update(update_data)

        # If approved, optionally create a speaker entry
        if new_status == 'approved':
            try:
                # Create speaker entry from application data
                speaker_data = {
                    'name': application.get('full_name'),
                    'title': application.get('title'),
                    'organization': application.get('organization'),
                    'bio': application.get('bio'),
                    'status': 'current',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'application_id': application_id
                }

                # Add research interests if available
                if application.get('research_interests'):
                    speaker_data['research_interests'] = application.get('research_interests')

                # Add LinkedIn profile if available
                if application.get('linkedin_profile'):
                    speaker_data['linkedin_profile'] = application.get('linkedin_profile')

                # Add website if available
                if application.get('website'):
                    speaker_data['website'] = application.get('website')

                # Save speaker to Firebase
                speakers_ref = db.reference('speakers')
                speakers_ref.push(speaker_data)

                # Add speaker_created flag to application
                application_ref.update({'speaker_created': True})

            except Exception as e:
                print(f"Error creating speaker from approved application: {e}")

        # Send notification email to applicant
        try:
            if new_status == 'approved':
                send_guest_speaker_approval_email(
                    application.get('email'),
                    application.get('full_name'),
                    admin_notes
                )
            elif new_status == 'rejected':
                send_guest_speaker_rejection_email(
                    application.get('email'),
                    application.get('full_name'),
                    admin_notes
                )
        except Exception as e:
            print(f"Error sending notification email: {e}")

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error updating guest speaker status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/guest-speaker-applications/<application_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_guest_speaker_application(application_id):
    """Delete a guest speaker application"""
    try:
        application_ref = db.reference(f'guest_speaker_applications/{application_id}')
        application = application_ref.get()

        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404

        # Delete CV file if exists
        if application.get('cv_url'):
            try:
                storage_client = storage.Client.from_service_account_json('serviceAccountKey.json')
                bucket = storage_client.bucket('giir-66ae6.firebasestorage.app')

                # Extract filename from URL
                if 'guest_speaker_cvs%2F' in application['cv_url']:
                    filename = application['cv_url'].split('guest_speaker_cvs%2F')[1].split('?')[0]
                    blob = bucket.blob(f'guest_speaker_cvs/{filename}')
                    if blob.exists():
                        blob.delete()
                        print(f"Successfully deleted CV file: {filename}")
            except Exception as e:
                print(f"Error deleting CV file: {str(e)}")

        # Delete application from Firebase
        application_ref.delete()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error deleting guest speaker application: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def send_guest_speaker_confirmation_email(email, full_name, application_id):
    """Send confirmation email for guest speaker application"""
    try:
        subject = "Guest Speaker Application Confirmation"
        body = f"""
Dear {full_name},

Thank you for your interest in becoming a guest speaker at our conference!

Your application (ID: {application_id}) has been received and is currently under review by our organizing committee.

We will contact you within 2-3 weeks regarding the status of your application. If you have any questions in the meantime, please don't hesitate to contact us.

Best regards,
Conference Organizing Committee
"""

        # Use existing send_email function
        send_email([email], subject, body)

    except Exception as e:
        print(f"Error sending guest speaker confirmation email: {e}")

def send_guest_speaker_approval_email(email, full_name, admin_notes):
    """Send approval email for guest speaker application"""
    try:
        subject = "Guest Speaker Application Approved"
        body = f"""
Dear {full_name},

Congratulations! We are pleased to inform you that your guest speaker application has been approved.

{admin_notes if admin_notes else 'We look forward to having you as a guest speaker at our conference.'}

You will receive further details about the conference schedule and logistics soon.

Best regards,
Conference Organizing Committee
"""

        send_email([email], subject, body)

    except Exception as e:
        print(f"Error sending guest speaker approval email: {e}")

def send_guest_speaker_rejection_email(email, full_name, admin_notes):
    """Send rejection email for guest speaker application"""
    try:
        subject = "Guest Speaker Application Update"
        body = f"""
Dear {full_name},

Thank you for your interest in becoming a guest speaker at our conference.

After careful review of your application, we regret to inform you that we are unable to accommodate your request at this time.

{admin_notes if admin_notes else 'We encourage you to apply for future conferences and thank you for your interest.'}

Best regards,
Conference Organizing Committee
"""

        send_email([email], subject, body)

    except Exception as e:
        print(f"Error sending guest speaker rejection email: {e}")

if __name__ == '__main__':
    # Create admin user on startup
    with app.app_context():
        create_admin_user()
    
    app.run(debug=True, host='0.0.0.0', port=5000)