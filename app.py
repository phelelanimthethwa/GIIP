from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import firebase_admin
from firebase_admin import credentials, db, auth, firestore
from config import Config
import json
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import os
from google.cloud import storage
import base64
from dotenv import load_dotenv
from models.email_service import EmailService
import pytz
import requests

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Please install it using: pip install python-dotenv")
    def load_dotenv(): pass

load_dotenv()  # Add this before creating the Flask app

app = Flask(__name__)
app.config.from_object(Config)

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
    
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ.get('FIREBASE_DATABASE_URL', 'https://giir-66ae6-default-rtdb.firebaseio.com'),
        'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'giir-66ae6.appspot.com')
    })
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Error initializing Firebase: {str(e)}")
    raise

# Initialize Google Cloud Storage
try:
    if os.environ.get('FIREBASE_CREDENTIALS'):
        # In production, use credentials from environment variable
        storage_client = storage.Client.from_service_account_info(
            json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        )
        print("Using Google Cloud Storage credentials from environment variable")
    else:
        # In development, use service account file
        storage_client = storage.Client.from_service_account_json('serviceAccountKey.json')
        print("Using Google Cloud Storage credentials from serviceAccountKey.json")
    
    bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET')
    bucket = storage_client.bucket(bucket_name)

    # Create the bucket if it doesn't exist
    if not bucket.exists():
        bucket.create()
        # Make all objects in bucket publicly readable
        bucket.make_public(recursive=True)
        print(f"Created storage bucket: {bucket_name}")
    else:
        print(f"Using existing storage bucket: {bucket_name}")
except Exception as e:
    print(f"Error configuring storage bucket: {str(e)}")
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
        # Create datetime object
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        # Get timezone
        tz = pytz.timezone(timezone_str)
        
        # Localize the datetime
        local_dt = tz.localize(dt)
        
        return local_dt.isoformat()
    except Exception as e:
        print(f"Error formatting datetime: {str(e)}")
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
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip'}

# Add these constants near the top of the file
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
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

# Add this near the top with other upload folder configurations
app.config['COMMITTEE_UPLOAD_FOLDER'] = 'static/uploads/committee'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

class User(UserMixin):
    def __init__(self, uid, email, full_name, is_admin=False):
        self.id = uid
        self.email = email
        self.full_name = full_name
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    try:
        user = auth.get_user(user_id)
        # Get additional user data from Realtime Database
        ref = db.reference(f'users/{user_id}')
        user_data = ref.get()
        is_admin = user_data.get('is_admin', False) if user_data else False
        return User(user.uid, user.email, user.display_name, is_admin)
    except:
        return None

def send_confirmation_email(registration_data):
    return email_service.send_registration_confirmation(registration_data)

# Add this helper function near the top of the file
def get_site_design():
    design_ref = db.reference('site_design')
    return design_ref.get() or DEFAULT_THEME

@app.route('/')
def home():
    try:
        # Get home content
        content_ref = db.reference('home_content')
        home_content = content_ref.get() or {
            'welcome': {
                'title': 'Welcome to GIIR Conference 2024',
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
            },
            'vmo': {
                'vision': 'The Global Institute on Innovative Research (GIIR) is geared towards bringing researchers to share their innovative research findings in the global platform',
                'mission': 'GIIR\'s intention is to initiate, develop and promote research in the fields of Social, Economic, Information Technology, Education and Management Sciences',
                'objectives': 'To provide a world class platform for researchers to share their research findings.\nTo encourage researchers to identify significant research issues.\nTo help in the dissemination of researcher\'s work.'
            },
            'downloads': [],
            'supporters': [],
            'footer': {
                'contact_email': 'contact@giirconference.com',
                'contact_phone': '+1234567890',
                'social_media': {
                    'facebook': '',
                    'twitter': '',
                    'linkedin': ''
                },
                'address': 'Conference Venue, City, Country',
                'copyright': '© 2024 GIIR Conference. All rights reserved.'
            }
        }
        
        # Get downloads
        downloads_ref = db.reference('downloads')
        downloads = downloads_ref.get() or []
        
        return render_template('user/home.html', 
                             home_content=home_content,
                             downloads=downloads,
                             site_design=get_site_design())
    except Exception as e:
        flash(f'Error loading home page: {str(e)}', 'error')
        return render_template('user/home.html', 
                             home_content={
                                'welcome': {
                                    'title': 'Welcome to GIIR Conference 2024',
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
                                },
                                'vmo': {
                                    'vision': 'The Global Institute on Innovative Research (GIIR) is geared towards bringing researchers to share their innovative research findings in the global platform',
                                    'mission': 'GIIR\'s intention is to initiate, develop and promote research in the fields of Social, Economic, Information Technology, Education and Management Sciences',
                                    'objectives': 'To provide a world class platform for researchers to share their research findings.\nTo encourage researchers to identify significant research issues.\nTo help in the dissemination of researcher\'s work.'
                                },
                                'downloads': [],
                                'supporters': [],
                                'footer': {
                                    'contact_email': 'contact@giirconference.com',
                                    'contact_phone': '+1234567890',
                                    'social_media': {
                                        'facebook': '',
                                        'twitter': '',
                                        'linkedin': ''
                                    },
                                    'address': 'Conference Venue, City, Country',
                                    'copyright': '© 2024 GIIR Conference. All rights reserved.'
                                }
                             },
                             downloads=[],
                             site_design=get_site_design())

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
            ]
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
    return render_template('user/call_for_papers.html', site_design=get_site_design())

@app.route('/paper-submission', methods=['GET', 'POST'])
@login_required
def paper_submission():
    if request.method == 'POST':
        try:
            # Get form data
            paper_data = {
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
                    flash(f'Please fill in all required fields.', 'error')
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

            # Create a storage reference
            bucket = storage_client.bucket(app.config['FIREBASE_CONFIG']['storageBucket'])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'papers/{current_user.id}/{timestamp}_{secure_filename(file.filename)}'
            blob = bucket.blob(filename)
            
            # Upload the file
            blob.upload_from_string(
                file.read(),
                content_type=file.content_type
            )
            
            # Make the file accessible
            blob.make_public()
            
            # Add file info to paper data
            paper_data['file_path'] = filename
            paper_data['file_url'] = blob.public_url

            # Debug print before saving
            print("Saving paper data:", paper_data)

            # Store paper in Firebase
            papers_ref = db.reference('papers')
            new_paper = papers_ref.push(paper_data)
            paper_id = new_paper.key

            # Debug print after saving
            print("Paper saved with ID:", paper_id)

            # Send confirmation email
            try:
                email_service.send_paper_confirmation({
                    'authors': paper_data['authors'],
                    'paper_title': paper_data['paper_title'],
                    'presentation_type': paper_data['presentation_type'],
                    'paper_id': paper_id,
                    'user_email': current_user.email
                })
            except Exception as e:
                print(f"Error sending confirmation email: {str(e)}")

            flash('Paper submitted successfully! Check your email for confirmation.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"Error submitting paper: {str(e)}")  # Log the error
            flash(f'Error submitting paper: {str(e)}', 'error')
            return redirect(url_for('paper_submission'))

    return render_template('user/papers/submit.html', 
                         site_design=get_site_design())

@app.route('/author-guidelines')
def author_guidelines():
    try:
        # Get guidelines from Firebase
        guidelines_ref = db.reference('author_guidelines')
        guidelines = guidelines_ref.get() or {}
        
        return render_template('user/papers/guidelines.html', 
                             guidelines=guidelines,
                             site_design=get_site_design())
    except Exception as e:
        flash('Error loading author guidelines.', 'error')
        return redirect(url_for('home'))

@app.route('/venue')
def venue():
    try:
        # Get venue details from Firebase
        venue_ref = db.reference('venue_details')
        venue_details = venue_ref.get()
        
        if venue_details:
            # Clean and validate venue details
            required_fields = ['name', 'address', 'city', 'country', 'postal_code', 'phone', 'email']
            for field in required_fields:
                if not venue_details.get(field):
                    venue_details[field] = 'TBA'
            
            # Handle map URL
            if not venue_details.get('map_url'):
                # Default to OpenStreetMap if no map URL is provided
                address = f"{venue_details['address']}, {venue_details['city']}, {venue_details['country']}"
                venue_details['map_url'] = f"https://www.openstreetmap.org/export/embed.html?bbox=-180,-90,180,90"
    
    except Exception as e:
        print(f"Error fetching venue details: {e}")
        venue_details = None
    
    return render_template('user/venue.html', venue_details=venue_details, site_design=get_site_design())

@app.route('/video-conference')
def video_conference():
    return render_template('user/video_conference.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('user/account/profile.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            # First verify the user exists
            try:
                user = auth.get_user_by_email(email)
            except:
                flash('Invalid email or password', 'error')
                return render_template('user/auth/login.html', site_design=get_site_design())

            # Debug: Print API key
            api_key = os.environ.get('FIREBASE_API_KEY')
            print(f"Using API key: {api_key}")
            
            if not api_key:
                api_key = app.config['FIREBASE_CONFIG']['apiKey']
                print(f"Fallback to config API key: {api_key}")

            # Verify password using Firebase Auth REST API
            verify_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            verify_data = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            headers = {"Content-Type": "application/json"}
            
            print(f"Making request to: {verify_url}?key={api_key}")
            response = requests.post(
                f"{verify_url}?key={api_key}",
                json=verify_data,
                headers=headers
            )

            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")

            if not response.ok:
                print(f"Login error: {response.text}")
                flash('Invalid email or password', 'error')
                return render_template('user/auth/login.html', site_design=get_site_design())
            
            # Get user data from Realtime Database
            ref = db.reference(f'users/{user.uid}')
            user_data = ref.get()
            
            if not user_data:
                # If user data doesn't exist in Realtime DB, create it
                user_data = {
                    'email': email,
                    'full_name': user.display_name or email.split('@')[0],
                    'created_at': datetime.now().isoformat(),
                    'is_admin': False
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
            
        except Exception as e:
            print(f"Login error: {str(e)}")  # Log the error
            flash('Invalid email or password', 'error')
            
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
            
            # Send welcome email
            email_service.send_welcome_email(user_data)
            
            flash('Account created successfully! Please check your email and login.', 'success')
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
        # Get registration fees from Firebase
        fees_ref = db.reference('registration_fees')
        fees = fees_ref.get()
        
        return render_template('user/registration.html', 
                             site_design=get_site_design(),
                             fees=fees)
    except Exception as e:
        flash('Error loading registration fees.', 'error')
        return render_template('user/registration.html', 
                             site_design=get_site_design(),
                             fees={})

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

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user's registrations
        registrations_ref = db.reference('registrations')
        registrations = registrations_ref.order_by_child('user_id').equal_to(current_user.id).get()
        
        # Get registration fees for displaying amounts
        fees_ref = db.reference('registration_fees')
        fees = fees_ref.get()
        
        return render_template('user/dashboard.html', 
                             registrations=registrations or {}, 
                             fees=fees,
                             site_design=get_site_design())
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('user/dashboard.html', 
                             registrations={}, 
                             fees={},
                             site_design=get_site_design())

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
        
        # Get all registrations
        reg_ref = db.reference('registrations')
        registrations = reg_ref.get() or {}
        
        # Get all submissions
        submissions_ref = db.reference('submissions')
        submissions = submissions_ref.get() or {}
        
        # Calculate stats
        stats = {
            'total_users': len(users) if users else 0,
            'total_registrations': len(registrations) if registrations else 0,
            'total_submissions': len(submissions) if submissions else 0,
            'pending_registrations': sum(1 for reg in registrations.values() if reg and reg.get('payment_status') == 'pending') if registrations else 0,
            'pending_submissions': sum(1 for sub in submissions.values() if sub and sub.get('status') == 'pending') if submissions else 0
        }
        
        # Get recent registrations and users (last 5)
        recent_registrations = {}
        recent_users = {}
        
        if registrations:
            # Sort registrations by created_at date
            sorted_registrations = sorted(
                [(k, v) for k, v in registrations.items() if v and v.get('created_at')],
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
                             site_design=get_site_design())
    except Exception as e:
        flash(f'Error loading admin dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html', 
                             users={}, 
                             registrations={},
                             stats={
                                'total_users': 0,
                                'total_registrations': 0,
                                'total_submissions': 0,
                                'pending_registrations': 0,
                                'pending_submissions': 0
                             },
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
            flash(f"Admin status updated successfully.", 'success')
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
            # Get currency settings
            currency_code = request.form.get('currency_code')
            custom_currency_symbol = request.form.get('custom_currency_symbol') if currency_code == 'custom' else None
            
            registration_fees = {
                'currency_code': currency_code,
                'custom_currency_symbol': custom_currency_symbol,
                'early_bird': None,
                'early': {
                    'deadline': request.form.get('early_deadline'),
                    'student_author': request.form.get('early_student'),
                    'regular_author': request.form.get('early_regular'),
                    'listener': request.form.get('early_listener'),
                    'virtual': request.form.get('early_virtual'),
                    'benefits': [benefit for benefit in request.form.getlist('early_benefits[]') if benefit.strip()]
                },
                'late': {
                    'deadline': request.form.get('late_deadline'),
                    'student_author': request.form.get('late_student'),
                    'regular_author': request.form.get('late_regular'),
                    'listener': request.form.get('late_listener'),
                    'virtual': request.form.get('late_virtual'),
                    'benefits': [benefit for benefit in request.form.getlist('late_benefits[]') if benefit.strip()]
                },
                'extra_paper_fee': request.form.get('extra_paper_fee'),
                'workshop_fee': request.form.get('workshop_fee'),
                'banquet_fee': request.form.get('banquet_fee'),
                'includes': request.form.getlist('registration_includes'),
                'payment_details': {
                    # South African Bank Details
                    'account_name': request.form.get('account_name'),
                    'account_number': request.form.get('account_number'),
                    'bank_name': request.form.get('bank_name'),
                    'universal_branch_code': request.form.get('universal_branch_code'),
                    'account_type': request.form.get('account_type'),
                    
                    # International Payment Details
                    'swift_code': request.form.get('swift_code'),
                    'iban': request.form.get('iban'),
                    'bank_address': request.form.get('bank_address'),
                    'intermediary_bank': request.form.get('intermediary_bank'),
                    
                    # Additional Information
                    'reference_format': request.form.get('reference_format'),
                    'contact_email': request.form.get('contact_email'),
                    'payment_instructions': request.form.get('payment_instructions')
                }
            }
            
            # Handle early bird registration if enabled
            if request.form.get('early_bird_enabled'):
                registration_fees['early_bird'] = {
                    'deadline': request.form.get('early_bird_deadline'),
                    'student_author': request.form.get('early_bird_student'),
                    'regular_author': request.form.get('early_bird_regular'),
                    'listener': request.form.get('early_bird_listener'),
                    'virtual': request.form.get('early_bird_virtual'),
                    'benefits': [benefit for benefit in request.form.getlist('early_bird_benefits[]') if benefit.strip()]
                }
            
            # Validate required fields
            required_fields = {
                'early': ['deadline', 'student_author', 'regular_author', 'listener', 'virtual'],
                'late': ['deadline', 'student_author', 'regular_author', 'listener', 'virtual'],
                'payment_details': ['account_name', 'account_number', 'bank_name', 'universal_branch_code', 'account_type']
            }
            
            errors = []
            
            # Validate early registration
            for field in required_fields['early']:
                if not registration_fees['early'][field]:
                    errors.append(f'Early registration {field.replace("_", " ")} is required')
            
            # Validate late registration
            for field in required_fields['late']:
                if not registration_fees['late'][field]:
                    errors.append(f'Late registration {field.replace("_", " ")} is required')
            
            # Validate payment details
            for field in required_fields['payment_details']:
                if not registration_fees['payment_details'][field]:
                    errors.append(f'Payment details {field.replace("_", " ")} is required')
            
            # Validate early bird if enabled
            if registration_fees['early_bird']:
                for field in required_fields['early']:
                    if not registration_fees['early_bird'][field]:
                        errors.append(f'Early bird {field.replace("_", " ")} is required')
            
            # Validate dates
            try:
                if registration_fees['early_bird']:
                    early_bird_deadline = datetime.strptime(registration_fees['early_bird']['deadline'], '%Y-%m-%d')
                    early_deadline = datetime.strptime(registration_fees['early']['deadline'], '%Y-%m-%d')
                    if early_bird_deadline >= early_deadline:
                        errors.append('Early bird deadline must be before early registration deadline')
                
                early_deadline = datetime.strptime(registration_fees['early']['deadline'], '%Y-%m-%d')
                late_deadline = datetime.strptime(registration_fees['late']['deadline'], '%Y-%m-%d')
                if early_deadline >= late_deadline:
                    errors.append('Early registration deadline must be before late registration deadline')
            except ValueError:
                errors.append('Invalid date format')
            
            if errors:
                for error in errors:
                    flash(error, 'danger')
                return redirect(url_for('admin_registration_fees'))
            
            # Update registration fees in Firebase
            db.reference('registration_fees').set(registration_fees)
            flash('Registration fees updated successfully', 'success')
            return redirect(url_for('admin_registration_fees'))
            
        except Exception as e:
            flash(f'Error updating registration fees: {str(e)}', 'danger')
            return redirect(url_for('admin_registration_fees'))
    
    # Get current fees settings
    fees_ref = db.reference('registration_fees')
    current_fees = fees_ref.get() or {}
    
    # Add currency symbol if not present
    if 'currency_code' not in current_fees:
        current_fees['currency_code'] = 'ZAR'
        current_fees['currency_symbol'] = 'R'
    
    return render_template('admin/admin_registration_fees.html', 
                         site_design=get_site_design(), 
                         fees=current_fees)

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
                
                # Store file information in Firebase
                downloads_ref = db.reference('downloads')
                new_download = {
                    'title': request.form.get('title'),
                    'description': request.form.get('description'),
                    'file_url': f"/static/uploads/documents/{unique_filename}",
                    'file_type': filename.rsplit('.', 1)[1].lower(),
                    'file_size': file_size_str,
                    'uploaded_at': datetime.now().isoformat(),
                    'type': request.form.get('type', 'pdf')  # Default to pdf if not specified
                }
                downloads_ref.push(new_download)
                
                flash('File uploaded successfully!', 'success')
                return redirect(url_for('admin_downloads'))
                
            except Exception as e:
                flash(f'Error uploading file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type', 'error')
            return redirect(request.url)
    
    # Get all downloads for display
    downloads_ref = db.reference('downloads')
    downloads = downloads_ref.get()
    return render_template('admin/downloads.html', site_design=get_site_design(), downloads=downloads)

@app.route('/admin/downloads/delete/<download_id>', methods=['POST'])
@login_required
@admin_required
def delete_download(download_id):
    try:
        # Get download info
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
        registrations_ref = db.reference('registrations')
        registrations = registrations_ref.get()
        return render_template('admin/manage_registrations.html', 
                             site_design=get_site_design(), 
                             registrations=registrations or {})
    except Exception as e:
        flash('Error loading registrations: ' + str(e), 'error')
        return render_template('admin/manage_registrations.html', 
                             site_design=get_site_design(), 
                             registrations={})

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
                registration['payment_proof'] = registration['payment_proof'].replace('/static/uploads/', '')
            if registration.get('paper') and registration['paper'].get('file_path'):
                registration['paper']['file_path'] = registration['paper']['file_path'].replace('/static/uploads/', '')
            
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

def send_email(to, subject, body):
    """
    Helper function to send emails using Flask-Mail.
    
    Args:
        to (str): Recipient email address
        subject (str): Email subject
        body (str): Email body content
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body,
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_approval_email(email, registration):
    subject = "GIIR Conference 2024 - Registration Approved"
    body = f"""Dear {registration.get('full_name')},

Your registration for the GIIR Conference 2024 has been approved.

Registration Details:
- Type: {registration.get('registration_type', '').replace('_', ' ').title()}
- Period: {registration.get('registration_period', '').replace('_', ' ').title()}
- Total Amount: R {registration.get('total_amount')}

{'Your paper submission has been confirmed.' if 'author' in registration.get('registration_type', '') else ''}
{'Virtual access details will be sent closer to the conference date.' if 'virtual' in registration.get('registration_type', '') else ''}

Thank you for registering for GIIR Conference 2024.

Best regards,
GIIR Conference Team"""
    
    send_email(email, subject, body)

def send_rejection_email(email, registration):
    subject = "GIIR Conference 2024 - Registration Update"
    body = f"""Dear {registration.get('full_name')},

Your registration for the GIIR Conference 2024 requires attention.

Please log in to your dashboard to view the status of your registration and make any necessary updates.

If you have any questions, please contact us.

Best regards,
GIIR Conference Team"""
    
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
    subject = f'Update on your GIIR Conference Paper Submission'
    
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
            site_design=get_site_design()
        )
    except Exception as e:
        flash(f'Error loading announcements: {str(e)}', 'error')
        return render_template(
            'admin/announcements.html', 
            announcements={},
            site_design=get_site_design()
        )

def send_email(recipients, subject, body, attachments=None):
    """Send email using configured email settings"""
    try:
        # Get email settings from Firebase
        settings_ref = db.reference('email_settings')
        settings = settings_ref.get()
        
        if not settings:
            raise Exception("Email settings not configured")
        
        # Configure Flask-Mail with settings
        app.config.update(
            MAIL_SERVER=settings.get('smtp_host'),
            MAIL_PORT=settings.get('smtp_port'),
            MAIL_USE_TLS=settings.get('use_tls', True),
            MAIL_USE_SSL=settings.get('use_ssl', False),
            MAIL_USERNAME=settings.get('email'),
            MAIL_PASSWORD=settings.get('password'),
            MAIL_DEFAULT_SENDER=f"GIIR Conference <{settings.get('email')}>"
        )
        
        # Create new Mail instance with current config
        mail = Mail(app)
        
        # Create message
        msg = Message(
            subject=subject,
            recipients=recipients if isinstance(recipients, list) else [recipients],
            body=body
        )
        
        # Add attachments if any
        if attachments:
            for attachment in attachments:
                msg.attach(
                    filename=os.path.basename(attachment['path']),
                    content_type=attachment['type'],
                    data=attachment['data']
                )
        
        # Send email
        with app.app_context():
            mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise

@app.route('/admin/announcements', methods=['POST'])
@login_required
@admin_required
def create_announcement():
    try:
        print("Creating new announcement...")
        
        # Create announcements upload directory if it doesn't exist
        upload_path = os.path.join(app.static_folder, 'uploads', 'announcements')
        os.makedirs(upload_path, exist_ok=True)
        
        # Get form data
        title = request.form.get('title')
        content = request.form.get('content')
        announcement_type = request.form.get('type')
        is_pinned = request.form.get('is_pinned') == 'on'
        should_send_email = request.form.get('send_email') == 'on'  # Renamed variable
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
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Handle image upload
        image_url = None
        image_data = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_image_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"announcement_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file_path = os.path.join(upload_path, unique_filename)
                file.save(file_path)
                image_url = f"/static/uploads/announcements/{unique_filename}"
                print("Image saved:", image_url)
                # Store image data for email attachment
                with open(file_path, 'rb') as f:
                    image_data = f.read()
        
        # Format the datetime with timezone
        formatted_datetime = format_datetime_with_timezone(
            scheduled_date,
            scheduled_time,
            timezone
        )
        
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
        
        print("Saving announcement to Firebase...")
        
        # Save to Firebase
        announcements_ref = db.reference('announcements')
        new_announcement = announcements_ref.push(announcement)
        
        print("Announcement saved successfully with ID:", new_announcement.key)
        
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
                    print(f"Sending email to {len(recipient_emails)} recipients")
                    
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
                        body = f'''
                        A new announcement has been posted:
                        
                        {title}
                        
                        {content}
                        
                        Scheduled for: {scheduled_date} at {scheduled_time} ({timezone})
                        
                        Best regards,
                        Conference Team
                        '''
                    
                    attachments = []
                    if image_url and image_data:
                        attachments.append({
                            'path': image_url,
                            'type': 'image/jpeg',
                            'data': image_data
                        })
                    
                    send_email(recipient_emails, subject, body, attachments)
                    email_status = f"Email notifications sent successfully to {len(recipient_emails)} recipients."
                    print(email_status)
                else:
                    email_status = "No users found to send email notifications."
                    print(email_status)
            except Exception as e:
                error_msg = f"Error sending email notification: {str(e)}"
                print("Error:", error_msg)
                email_status = error_msg
        
        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            return jsonify({
                'success': True, 
                'id': new_announcement.key,
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
        print("Error:", error_msg)
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
        # Get form data
        title = request.form.get('title')
        content = request.form.get('content')
        announcement_type = request.form.get('type')
        is_pinned = request.form.get('is_pinned') == 'on'
        send_email = request.form.get('send_email') == 'on'
        scheduled_date = request.form.get('announcement_date')
        scheduled_time = request.form.get('announcement_time')
        timezone = request.form.get('timezone')
        
        # Update announcement
        announcement_ref = db.reference(f'announcements/{announcement_id}')
        current_announcement = announcement_ref.get()
        
        if not current_announcement:
            return jsonify({'success': False, 'error': 'Announcement not found'}), 404
        
        # Handle image upload
        image_url = current_announcement.get('image_url')
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_image_file(file.filename):
                # Delete old image if exists
                if image_url:
                    old_image_path = os.path.join(app.static_folder, image_url.lstrip('/static/'))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image
                filename = secure_filename(file.filename)
                unique_filename = f"announcement_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                upload_path = os.path.join(app.static_folder, 'uploads', 'announcements')
                os.makedirs(upload_path, exist_ok=True)
                file_path = os.path.join(upload_path, unique_filename)
                file.save(file_path)
                image_url = f"/static/uploads/announcements/{unique_filename}"
        
        # Format the datetime with timezone
        formatted_datetime = format_datetime_with_timezone(
            scheduled_date,
            scheduled_time,
            timezone
        )
        
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
        
        announcement_ref.update(update_data)
        
        # Send email notification if requested
        email_status = None
        if send_email:
            try:
                # Get all user emails
                users_ref = db.reference('users')
                users = users_ref.get()
                if users:
                    recipient_emails = [user['email'] for user in users.values() if user.get('email')]
                    
                    msg = Message(
                        f'Announcement Update: {title}',
                        recipients=recipient_emails,
                        body=f'''
                        An announcement has been updated:
                        
                        {title}
                        
                        {content}
                        
                        Scheduled for: {scheduled_date} at {scheduled_time} ({timezone})
                        
                        Best regards,
                        Conference Team
                        '''
                    )
                    
                    # Add image attachment if exists
                    if image_url:
                        with app.open_resource(os.path.join(app.static_folder, image_url.lstrip('/static/'))) as fp:
                            msg.attach(
                                os.path.basename(image_url),
                                'image/jpeg',
                                fp.read()
                            )
                    
                    mail.send(msg)
                    email_status = "Email notifications sent successfully."
            except Exception as e:
                error_msg = f"Error sending email notification: {str(e)}"
                print("Error:", error_msg)
                email_status = error_msg
        
        return jsonify({
            'success': True,
            'emailStatus': email_status
        })
    except Exception as e:
        error_msg = f"Error updating announcement: {str(e)}"
        print("Error:", error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/admin/announcements/<announcement_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    try:
        # Delete announcement from Firebase
        announcement_ref = db.reference(f'announcements/{announcement_id}')
        announcement = announcement_ref.get()
        
        if not announcement:
            return jsonify({'success': False, 'error': 'Announcement not found'}), 404
        
        # Delete associated image if exists
        if announcement.get('image_url'):
            image_path = os.path.join(app.static_folder, announcement['image_url'].lstrip('/static/'))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        announcement_ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        error_msg = f"Error deleting announcement: {str(e)}"
        print("Error:", error_msg)
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

@app.route('/admin/home-content', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_home_content():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for('login', next=request.url))

    # Define default content structure
    default_content = {
        'welcome': {
            'title': 'Welcome to GIIR Conference 2024',
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
        },
        'vmo': {
            'vision': 'The Global Institute on Innovative Research (GIIR) is geared towards bringing researchers to share their innovative research findings in the global platform',
            'mission': 'GIIR\'s intention is to initiate, develop and promote research in the fields of Social, Economic, Information Technology, Education and Management Sciences',
            'objectives': 'To provide a world class platform for researchers to share their research findings.\nTo encourage researchers to identify significant research issues.\nTo help in the dissemination of researcher\'s work.'
        },
        'downloads': [],
        'supporters': [],
        'footer': {
            'contact_email': 'contact@giirconference.com',
            'contact_phone': '+1234567890',
            'social_media': {
                'facebook': '',
                'twitter': '',
                'linkedin': ''
            },
            'address': 'Conference Venue, City, Country',
            'copyright': '© 2024 GIIR Conference. All rights reserved.'
        }
    }

    if request.method == 'POST':
        try:
            # Get existing content first
            content_ref = db.reference('home_content')
            existing_content = content_ref.get() or default_content
            
            # Handle hero images
            hero_images = []
            
            # Add existing images that weren't deleted
            if 'existing_images' in request.form:
                try:
                    existing_images = json.loads(request.form['existing_images'])
                    hero_images.extend(existing_images)
                except json.JSONDecodeError:
                    pass
            
            # Handle new hero image uploads
            if 'hero_images' in request.files:
                files = request.files.getlist('hero_images')
                for file in files:
                    if file and file.filename and allowed_image_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        
                        # Create uploads directory if it doesn't exist
                        upload_path = os.path.join(app.static_folder, 'uploads', 'hero')
                        os.makedirs(upload_path, exist_ok=True)
                        
                        file_path = os.path.join(upload_path, unique_filename)
                        file.save(file_path)
                        
                        hero_images.append({
                            'url': f"/static/uploads/hero/{unique_filename}",
                            'alt': filename
                        })

            # Handle downloads
            downloads = []
            download_titles = request.form.getlist('download_titles[]')
            download_descriptions = request.form.getlist('download_descriptions[]')
            download_ids = request.form.getlist('download_ids[]')
            download_existing_files = request.form.getlist('download_existing_files[]')

            for i in range(len(download_titles)):
                download = {
                    'id': download_ids[i] if i < len(download_ids) else f'download_{len(downloads)}',
                    'title': download_titles[i],
                    'description': download_descriptions[i],
                    'file_url': download_existing_files[i] if i < len(download_existing_files) else '',
                    'file_type': '',
                    'file_size': ''
                }

                # Check if there's a new file upload for this download
                file_key = f'download_file_{download["id"]}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                        
                        # Create downloads directory if it doesn't exist
                        upload_path = os.path.join(app.static_folder, 'uploads', 'downloads')
                        os.makedirs(upload_path, exist_ok=True)
                        
                        file_path = os.path.join(upload_path, unique_filename)
                        file.save(file_path)
                        
                        # Update download info
                        download['file_url'] = f"/static/uploads/downloads/{unique_filename}"
                        download['file_type'] = filename.rsplit('.', 1)[1].lower()
                        download['file_size'] = f"{os.path.getsize(file_path) / 1024:.0f} KB"
                elif download['file_url']:  # Keep existing file info if no new file uploaded
                    existing_download = next((d for d in existing_content.get('downloads', []) 
                                           if d.get('file_url') == download['file_url']), None)
                    if existing_download:
                        download['file_type'] = existing_download.get('file_type', '')
                        download['file_size'] = existing_download.get('file_size', '')

                downloads.append(download)

            # Handle supporters
            supporters = []
            
            # Handle existing supporters
            existing_names = request.form.getlist('existing_supporter_names[]')
            existing_descriptions = request.form.getlist('existing_supporter_descriptions[]')
            existing_logos = request.form.getlist('existing_supporter_logos[]')
            
            for i in range(len(existing_names)):
                if existing_names[i].strip() and existing_logos[i].strip():
                    supporters.append({
                        'name': existing_names[i],
                        'description': existing_descriptions[i],
                        'logo': existing_logos[i]
                    })
            
            # Handle new supporters
            new_names = request.form.getlist('new_supporter_names[]')
            new_descriptions = request.form.getlist('new_supporter_descriptions[]')
            new_logos = request.form.getlist('new_supporter_logos[]')
            
            for i in range(len(new_names)):
                if new_names[i].strip() and new_logos[i].strip():
                    # Convert data URL to file and save
                    try:
                        # Extract the base64 part of the data URL
                        image_data = new_logos[i].split(',')[1]
                        image_binary = base64.b64decode(image_data)
                        
                        # Generate unique filename
                        filename = f"supporter_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.png"
                        
                        # Create supporters directory if it doesn't exist
                        upload_path = os.path.join(app.static_folder, 'uploads', 'supporters')
                        os.makedirs(upload_path, exist_ok=True)
                        
                        # Save the image
                        file_path = os.path.join(upload_path, filename)
                        with open(file_path, 'wb') as f:
                            f.write(image_binary)
                        
                        # Add to supporters list
                        supporters.append({
                            'name': new_names[i],
                            'description': new_descriptions[i],
                            'logo': f"/static/uploads/supporters/{filename}"
                        })
                    except Exception as e:
                        print(f"Error saving supporter image: {str(e)}")
                        continue

            # Get form data
            home_content = {
                'welcome': {
                    'title': request.form.get('welcome[title]'),
                    'message': request.form.get('welcome[message]')
                },
                'hero': {
                    'images': hero_images,
                    'conference': {
                        'name': request.form.get('conference[name]'),
                        'date': request.form.get('conference[date]'),
                        'time': request.form.get('conference[time]'),
                        'city': request.form.get('conference[city]'),
                        'highlights': request.form.get('conference[highlights]')
                    }
                },
                'vmo': {
                    'vision': request.form.get('vmo[vision]'),
                    'mission': request.form.get('vmo[mission]'),
                    'objectives': request.form.get('vmo[objectives]')
                },
                'downloads': downloads,
                'supporters': supporters,
                'footer': {
                    'contact_email': request.form.get('footer[contact_email]'),
                    'contact_phone': request.form.get('footer[contact_phone]'),
                    'social_media': {
                        'facebook': request.form.get('footer[social_media][facebook]'),
                        'twitter': request.form.get('footer[social_media][twitter]'),
                        'linkedin': request.form.get('footer[social_media][linkedin]')
                    },
                    'address': request.form.get('footer[address]'),
                    'copyright': request.form.get('footer[copyright]')
                },
                'updated_at': datetime.now().isoformat(),
                'updated_by': current_user.email
            }
            
            # Save to Firebase
            content_ref = db.reference('home_content')
            content_ref.set(home_content)
            
            flash('Home content updated successfully!', 'success')
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error saving home content: {str(e)}")  # Add debug print
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET request - render template with current content
    try:
        content_ref = db.reference('home_content')
        home_content = content_ref.get() or default_content
        return render_template('admin/home_content.html', 
                             home_content=home_content,
                             site_design=get_site_design())
    except Exception as e:
        flash(f'Error loading home content: {str(e)}', 'error')
        return render_template('admin/home_content.html', 
                             home_content=default_content,
                             site_design=get_site_design())

# Add to admin_required routes list in base_admin.html
@app.context_processor
def inject_admin_menu():
    admin_menu = [
        {'url': 'admin_dashboard', 'icon': 'tachometer-alt', 'text': 'Dashboard'},
        {'url': 'admin_home_content', 'icon': 'home', 'text': 'Home Content'},
        {'url': 'admin_about_content', 'icon': 'info-circle', 'text': 'About Content'},
        {'url': 'admin_users', 'icon': 'users', 'text': 'Users'},
        {'url': 'admin_registrations', 'icon': 'clipboard-list', 'text': 'Registrations'},
        {'url': 'admin_papers', 'icon': 'file-alt', 'text': 'Submissions'},  # Updated this line
        {'url': 'admin_schedule', 'icon': 'calendar-alt', 'text': 'Schedule'},
        {'url': 'admin_venue', 'icon': 'map-marker-alt', 'text': 'Venue'},
        {'url': 'admin_registration_fees', 'icon': 'dollar-sign', 'text': 'Registration Fees'},
        {'url': 'admin_announcements', 'icon': 'bullhorn', 'text': 'Announcements'},
        {'url': 'admin_downloads', 'icon': 'download', 'text': 'Downloads'},
        {'url': 'admin_author_guidelines', 'icon': 'book', 'text': 'Author Guidelines'},
        {'url': 'admin_email_templates', 'icon': 'envelope', 'text': 'Email Templates'},
        {'url': 'admin_email_settings', 'icon': 'envelope-open', 'text': 'Email Settings'},
        {'url': 'admin_design', 'icon': 'palette', 'text': 'Site Design'}
    ]
    return dict(admin_menu=admin_menu)

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
                'hero_text_color': request.form.get('hero_text_color', DEFAULT_THEME['hero_text_color'])
            }
            
            # Save theme data to Firebase
            design_ref = db.reference('site_design')
            design_ref.set(theme_data)
            
            flash('Site design updated successfully!', 'success')
            return redirect(url_for('admin_design'))
            
        except Exception as e:
            flash(f'Error updating site design: {str(e)}', 'error')
            return redirect(url_for('admin_design'))
    
    # Get current design settings
    design_ref = db.reference('site_design')
    current_design = design_ref.get() or DEFAULT_THEME
    
    return render_template('admin/design.html', site_design=get_site_design(), design=current_design)

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
    except Exception as e:
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
                ]
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
            ]
        }
        
        return render_template('admin/about_content.html', 
                             about_content=about_content,
                             site_design=get_site_design())
        
    except Exception as e:
        flash(f'Error managing about content: {str(e)}', 'error')
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
                'early_bird': None,  # Early bird is optional
                'early': {
                    'deadline': '',
                    'student_author': '',
                    'regular_author': '',
                    'listener': '',
                    'virtual': '',
                    'benefits': []
                },
                'late': {
                    'deadline': '',
                    'student_author': '',
                    'regular_author': '',
                    'listener': '',
                    'virtual': '',
                    'benefits': []
                },
                'extra_paper_fee': '',
                'workshop_fee': '',
                'banquet_fee': '',
                'includes': [],
                'payment_details': {
                    # South African Bank Details
                    'account_name': '',
                    'account_number': '',
                    'bank_name': '',
                    'universal_branch_code': '',
                    'account_type': '',
                    
                    # Additional Information
                    'reference_format': '',
                    'contact_email': '',
                    'payment_instructions': ''
                }
            }
        
        return fees
    except Exception as e:
        print(f"Error fetching registration fees: {str(e)}")
        return None

@app.route('/registration-form', methods=['GET', 'POST'])
@login_required
def registration_form():
    # Get registration type and period from query parameters
    registration_type = request.args.get('type')
    registration_period = request.args.get('period')
    
    # Get fees from Firebase
    fees_ref = db.reference('registration_fees')
    fees = fees_ref.get()
    
    if request.method == 'POST':
        try:
            # Create upload directories if they don't exist
            papers_dir = os.path.join(app.static_folder, 'uploads', 'papers')
            payments_dir = os.path.join(app.static_folder, 'uploads', 'payments')
            os.makedirs(papers_dir, exist_ok=True)
            os.makedirs(payments_dir, exist_ok=True)
            
            # Get registration fee with default value of 0
            try:
                registration_fee = float(request.form.get('registration_fee', 0))
            except (ValueError, TypeError):
                registration_fee = 0
            
            # Handle payment proof upload
            payment_proof_url = ''
            if 'payment_proof' in request.files:
                payment_file = request.files['payment_proof']
                if payment_file and payment_file.filename:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = secure_filename(f"{timestamp}_{payment_file.filename}")
                    payment_path = os.path.join(payments_dir, filename)
                    payment_file.save(payment_path)
                    payment_proof_url = f"/static/uploads/payments/{filename}"
            
            # Get form data
            registration_data = {
                'user_id': current_user.id,
                'email': current_user.email,
                'full_name': current_user.full_name,
                'institution': request.form.get('institution'),
                'registration_type': request.form.get('registration_type'),
                'registration_period': request.form.get('registration_period'),
                'registration_fee': registration_fee,
                'workshop': request.form.get('workshop') == 'on',
                'banquet': request.form.get('banquet') == 'on',
                'extra_paper': request.form.get('extra_paper') == 'on',
                'payment_reference': request.form.get('payment_reference'),
                'payment_proof_url': payment_proof_url,
                'submission_date': datetime.now().isoformat(),
                'payment_status': 'pending',
                'total_amount': float(request.form.get('total_amount', 0)),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save to Firebase
            registrations_ref = db.reference('registrations')
            new_registration = registrations_ref.push(registration_data)
            
            # Also save reference to user's registrations
            user_reg_ref = db.reference(f'users/{current_user.id}/registrations/{new_registration.key}')
            user_reg_ref.set(True)
            
            flash('Registration submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error submitting registration: {str(e)}', 'error')
            return render_template('user/registration.html',
                                site_design=get_site_design(),
                                fees=fees,
                                firebase_config=app.config['FIREBASE_CONFIG'],
                                selected_type=registration_type,
                                selected_period=registration_period)
    
    # If registration type or period is missing, redirect to registration page
    if not registration_type or not registration_period:
        flash('Please select a registration type and period first.', 'error')
        return redirect(url_for('registration'))
    
    return render_template('user/registration.html',
                         site_design=get_site_design(),
                         fees=fees,
                         firebase_config=app.config['FIREBASE_CONFIG'],
                         selected_type=registration_type,
                         selected_period=registration_period)

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
                'virtual_guidelines': request.form.get('virtual_guidelines', '')
            }

            # Handle template file uploads
            if 'abstract_template' in request.files:
                file = request.files['abstract_template']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"abstract_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    upload_path = os.path.join(app.static_folder, 'uploads', 'templates')
                    os.makedirs(upload_path, exist_ok=True)
                    file.save(os.path.join(upload_path, unique_filename))
                    new_guidelines['abstract_template'] = f"/static/uploads/templates/{unique_filename}"

            if 'paper_template' in request.files:
                file = request.files['paper_template']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"paper_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    upload_path = os.path.join(app.static_folder, 'uploads', 'templates')
                    os.makedirs(upload_path, exist_ok=True)
                    file.save(os.path.join(upload_path, unique_filename))
                    new_guidelines['paper_template'] = f"/static/uploads/templates/{unique_filename}"

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

# Admin paper management routes
@app.route('/admin/submissions')  # Keep this route for backward compatibility
@app.route('/admin/papers')
@login_required
@admin_required
def admin_papers():
    try:
        # Get all papers from Firebase
        papers_ref = db.reference('papers')
        papers = papers_ref.get() or {}
        
        # Debug print to check what's being retrieved
        print("Retrieved papers:", papers)
        
        # Sort papers by submission date (newest first)
        papers = dict(sorted(
            papers.items(),
            key=lambda x: x[1].get('submitted_at', ''),
            reverse=True
        ))
        
        return render_template(
            'admin/submissions.html',
            submissions=papers,
            site_design=get_site_design()
        )
    except Exception as e:
        print(f"Error in admin_papers: {str(e)}")  # Add debug print
        flash(f'Error loading papers: {str(e)}', 'error')
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
        with mail.connect() as conn:
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
            except:
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
            except Exception as e:
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
            
            # Validate reCAPTCHA
            recaptcha_response = request.form.get('g-recaptcha-response')
            if not recaptcha_response:
                return jsonify({'success': False, 'message': 'Please complete the reCAPTCHA verification.'})

            # Validate required fields
            if not all([name, email, subject, message]):
                return jsonify({'success': False, 'message': 'Please fill in all required fields.'})

            # Store contact submission in Firebase
            contact_ref = db.reference('contact_submissions')
            submission_data = {
                'name': name,
                'email': email,
                'subject': subject,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'status': 'new'  # For tracking response status
            }
            contact_ref.push(submission_data)

            # Send email notification to admin
            try:
                msg = Message(
                    subject=f'New Contact Form Submission: {subject}',
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[app.config['ADMIN_EMAIL']],
                    body=f'''New contact form submission received:

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}
'''
                )
                mail.send(msg)
            except Exception as e:
                print(f"Error sending email notification: {str(e)}")
                # Continue execution even if email fails

            return jsonify({'success': True})

        except Exception as e:
            print(f"Error processing contact form: {str(e)}")
            return jsonify({'success': False, 'message': 'An error occurred while processing your request.'})

    # GET request - display contact form
    return render_template('contact.html', 
                         recaptcha_site_key=app.config['RECAPTCHA_SITE_KEY'],
                         site_design=get_site_design())

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
        if not '.' in paper_file.filename or \
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

if __name__ == '__main__':
    create_admin_user()  # Create admin user when starting the app
    
    # Use production settings if not in debug mode
    if os.environ.get('FLASK_ENV') == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['REMEMBER_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['REMEMBER_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
    else:
        app.run(debug=True) 