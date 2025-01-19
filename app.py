from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import firebase_admin
from firebase_admin import credentials, db, auth
from config import Config
import json
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
import os
from google.cloud import storage

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Firebase Admin SDK
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': Config.FIREBASE_CONFIG['databaseURL']
})

# Initialize Google Cloud Storage with the same credentials
storage_client = storage.Client.from_service_account_json('serviceAccountKey.json')

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Flask-Mail
mail = Mail(app)

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

# Add this configuration after other app configurations
app.config['UPLOAD_FOLDER'] = 'static/uploads/documents'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
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
    'hero_text_color': '#ffffff',
    'hero_image': '/static/uploads/design/default-hero.jpg'  # Add default hero image
}

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
    try:
        msg = Message('Conference Registration Confirmation',
                     recipients=[registration_data['email']])
        msg.body = f"""
        Dear {registration_data['full_name']},
        
        Thank you for registering for Conference 2024!
        
        Registration Details:
        - Registration Type: {registration_data['registration_type']}
        - Total Amount: ${registration_data['total_amount']}
        - Workshop: {'Yes' if registration_data.get('workshop') else 'No'}
        - Banquet: {'Yes' if registration_data.get('banquet') else 'No'}
        
        Please keep this email for your records.
        
        Best regards,
        Conference Team
        """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# Add this helper function near the top of the file
def get_site_design():
    design_ref = db.reference('site_design')
    return design_ref.get() or DEFAULT_THEME

@app.route('/')
def home():
    downloads_ref = db.reference('downloads')
    downloads = downloads_ref.get()
    return render_template('user/home.html', downloads=downloads, site_design=get_site_design())

@app.route('/about')
def about():
    return render_template('user/about.html', site_design=get_site_design())

@app.route('/call-for-papers')
def call_for_papers():
    return render_template('user/call_for_papers.html', site_design=get_site_design())

@app.route('/paper-submission', methods=['GET', 'POST'])
@login_required
def paper_submission():
    if request.method == 'POST':
        try:
            # Verify reCAPTCHA
            recaptcha_response = request.form.get('g-recaptcha-response')
            if not recaptcha_response:
                flash('Please complete the reCAPTCHA.', 'error')
                return redirect(url_for('paper_submission'))

            # Get form data
            submission_data = {
                'name': request.form.get('name'),
                'email': request.form.get('email'),
                'country_code': request.form.get('country_code'),
                'mobile': request.form.get('mobile'),
                'paper_title': request.form.get('paper_title'),
                'university': request.form.get('university'),
                'conference_name': request.form.get('conference_name'),
                'conference_date': request.form.get('conference_date'),
                'conference_city': request.form.get('conference_city'),
                'conference_country': request.form.get('conference_country'),
                'presentation_mode': request.form.get('presentation_mode'),
                'journal': request.form.get('journal'),
                'comments': request.form.get('comments'),
                'submitted_at': datetime.now().isoformat(),
                'status': 'pending'
            }

            # Handle file upload
            if 'paper_file' in request.files:
                file = request.files['paper_file']
                if file and file.filename:
                    # Create a storage reference
                    bucket = storage.bucket()
                    blob = bucket.blob(f'papers/{datetime.now().strftime("%Y%m%d_%H%M%S")}_{secure_filename(file.filename)}')
                    
                    # Upload the file
                    blob.upload_from_string(
                        file.read(),
                        content_type=file.content_type
                    )
                    
                    # Make the file publicly accessible
                    blob.make_public()
                    
                    # Add file URL to submission data
                    submission_data['file_url'] = blob.public_url

            # Store submission in Firebase
            ref = db.reference('submissions')
            new_submission = ref.push(submission_data)
            
            # Send confirmation email
            try:
                msg = Message('Paper Submission Confirmation',
                            recipients=[submission_data['email']])
                msg.body = f"""
                Dear {submission_data['name']},
                
                Thank you for submitting your paper to Conference 2024.
                
                Submission Details:
                - Paper Title: {submission_data['paper_title']}
                - Presentation Mode: {submission_data['presentation_mode']}
                - Submission ID: {new_submission.key}
                
                We will review your submission and get back to you soon.
                
                Best regards,
                Conference Team
                """
                mail.send(msg)
            except Exception as e:
                print(f"Error sending email: {str(e)}")

            flash('Paper submitted successfully! Check your email for confirmation.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error submitting paper: {str(e)}', 'error')
            return redirect(url_for('paper_submission'))

    return render_template('user/papers/submit.html', site_design=get_site_design(), recaptcha_site_key=app.config['RECAPTCHA_SITE_KEY'])

@app.route('/author-guidelines')
def author_guidelines():
    return render_template('user/papers/guidelines.html')

@app.route('/venue')
def venue():
    # Get venue details from Firebase
    venue_ref = db.reference('venue')
    venue_details = venue_ref.get()
    return render_template('user/conference/venue.html', site_design=get_site_design(), venue_details=venue_details)

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
            user = auth.get_user_by_email(email)
            # Get user data from Realtime Database
            ref = db.reference(f'users/{user.uid}')
            user_data = ref.get()
            is_admin = user_data.get('is_admin', False) if user_data else False
            
            # In a real application, you would verify the password here
            # For demo purposes, we're just logging in the user
            login_user(User(user.uid, user.email, user.display_name, is_admin))
            flash('Logged in successfully!', 'success')
            
            # Redirect admin users to admin dashboard
            if is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        except:
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
            return render_template('user/auth/register.html', site_design=get_site_design())

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('user/auth/register.html', site_design=get_site_design())

        try:
            # Create user in Firebase Authentication
            user = auth.create_user(
                email=email,
                password=password,
                display_name=full_name
            )
            # Store additional user data in Realtime Database
            ref = db.reference('users')
            ref.child(user.uid).set({
                'email': email,
                'full_name': full_name,
                'created_at': datetime.now().isoformat(),
                'is_admin': False  # Default to normal user
            })
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'error')
            return render_template('user/auth/register.html', site_design=get_site_design())
    
    return render_template('user/auth/register.html', site_design=get_site_design())

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/registration', methods=['GET', 'POST'])
@login_required
def registration():
    # Get registration fees from Firebase
    fees = db.reference('registration_fees').get()
    
    if request.method == 'POST':
        registration_data = {
            'full_name': request.form.get('full_name'),
            'email': current_user.email,
            'affiliation': request.form.get('affiliation'),
            'registration_type': request.form.get('registration_type'),
            'paper_id': request.form.get('paper_id'),
            'workshop': request.form.get('workshop') == 'yes',
            'banquet': request.form.get('banquet') == 'yes',
            'dietary': request.form.get('dietary'),
            'created_at': datetime.now().isoformat()
        }
        
        # Calculate total amount based on registration type and period
        total = 0
        current_date = datetime.now()
        
        if fees:
            # Determine registration period
            if fees.get('early_bird') and current_date <= datetime.strptime(fees['early_bird']['deadline'], '%Y-%m-%d'):
                period = fees['early_bird']
            elif fees.get('early') and current_date <= datetime.strptime(fees['early']['deadline'], '%Y-%m-%d'):
                period = fees['early']
            else:
                period = fees.get('late', {})
            
            # Get base fee
            if registration_data['registration_type'] == 'student':
                total = float(period.get('student_author', 0))
            elif registration_data['registration_type'] == 'regular':
                total = float(period.get('regular_author', 0))
            elif registration_data['registration_type'] == 'listener':
                total = float(period.get('listener', 0))
            elif registration_data['registration_type'] == 'virtual':
                total = float(period.get('virtual', 0))
            
            # Add extra fees
            if registration_data['workshop']:
                total += 50  # Workshop fee
            if registration_data['banquet']:
                total += 75  # Banquet fee
        
        registration_data['total_amount'] = total
        registration_data['payment_status'] = 'pending'
        
        try:
            # Store registration in Firebase
            ref = db.reference('registrations')
            new_reg = ref.push(registration_data)
            
            # Send confirmation email
            if send_confirmation_email(registration_data):
                flash('Registration successful! Check your email for confirmation.', 'success')
            else:
                flash('Registration successful but email confirmation failed.', 'warning')
            
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error processing registration: {str(e)}', 'error')
    
    return render_template('user/registration.html', site_design=get_site_design(), fees=fees)

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user's registrations
        registrations_ref = db.reference(f'registrations').order_by_child('user_id').equal_to(current_user.id)
        registrations = registrations_ref.get()
        return render_template('user/account/dashboard.html', registrations=registrations or {}, site_design=get_site_design())
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('user/account/dashboard.html', registrations={}, site_design=get_site_design())

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
        users = users_ref.get()
        
        # Get all registrations
        reg_ref = db.reference('registrations')
        registrations = reg_ref.get()
        
        return render_template('admin/dashboard.html', 
                             users=users or {}, 
                             registrations=registrations or {})
    except Exception as e:
        flash(f'Error loading admin dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html', users={}, registrations={})

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
        admin_email = "admin@conference2024.com"
        admin_password = "Admin@2024"
        admin_name = "Conference Admin"

        # Create user in Firebase Authentication
        try:
            user = auth.create_user(
                email=admin_email,
                password=admin_password,
                display_name=admin_name
            )
        except auth.EmailAlreadyExistsError:
            # If user already exists, get the user
            user = auth.get_user_by_email(admin_email)

        # Store or update user data in Realtime Database
        ref = db.reference('users')
        ref.child(user.uid).set({
            'email': admin_email,
            'full_name': admin_name,
            'created_at': datetime.now().isoformat(),
            'is_admin': True
        })
        print("Admin user created successfully!")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        return True
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        return False

@app.route('/admin/venue', methods=['GET', 'POST'])
@admin_required
def admin_venue():
    if request.method == 'POST':
        venue_data = {
            'name': request.form.get('name'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'country': request.form.get('country'),
            'postal_code': request.form.get('postal_code'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'map_url': request.form.get('map_url'),
            'hotels': [],  # Will be updated separately
            'airport_transport': request.form.getlist('airport_transport'),
            'local_transport': request.form.getlist('local_transport'),
            'attractions': []  # Will be updated separately
        }
        
        # Update venue details in Firebase
        venue_ref = db.reference('venue')
        venue_ref.set(venue_data)
        
        flash('Venue details updated successfully', 'success')
        return redirect(url_for('admin_venue'))
    
    # Get current venue details
    venue_ref = db.reference('venue')
    venue_details = venue_ref.get()
    return render_template('admin/admin_venue.html', site_design=get_site_design(), venue_details=venue_details)

@app.route('/admin/registration-fees', methods=['GET', 'POST'])
@admin_required
def admin_registration_fees():
    if request.method == 'POST':
        registration_fees = {
            'early_bird': {
                'deadline': request.form.get('early_bird_deadline'),
                'student_author': request.form.get('early_bird_student'),
                'regular_author': request.form.get('early_bird_regular'),
                'listener': request.form.get('early_bird_listener'),
                'virtual': request.form.get('early_bird_virtual')
            },
            'early': {
                'deadline': request.form.get('early_deadline'),
                'student_author': request.form.get('early_student'),
                'regular_author': request.form.get('early_regular'),
                'listener': request.form.get('early_listener'),
                'virtual': request.form.get('early_virtual')
            },
            'late': {
                'deadline': request.form.get('late_deadline'),
                'student_author': request.form.get('late_student'),
                'regular_author': request.form.get('late_regular'),
                'listener': request.form.get('late_listener'),
                'virtual': request.form.get('late_virtual')
            },
            'extra_paper_fee': request.form.get('extra_paper_fee'),
            'includes': request.form.getlist('registration_includes'),
            'payment_details': {
                'beneficiary': request.form.get('beneficiary'),
                'iban': request.form.get('iban'),
                'bic': request.form.get('bic'),
                'beneficiary_address': request.form.get('beneficiary_address'),
                'bank_name': request.form.get('bank_name'),
                'bank_address': request.form.get('bank_address'),
                'intermediary_bic': request.form.get('intermediary_bic'),
                'contact_email': request.form.get('contact_email')
            }
        }
        
        # Update registration fees in Firebase
        db.reference('registration_fees').set(registration_fees)
        flash('Registration fees updated successfully', 'success')
        return redirect(url_for('admin_registration_fees'))
    
    # Get current registration fees
    fees = db.reference('registration_fees').get()
    return render_template('admin/admin_registration_fees.html', site_design=get_site_design(), fees=fees)

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
        # Get all registrations from Firebase
        registrations_ref = db.reference('registrations')
        registrations = registrations_ref.get()
        return render_template('admin/registrations.html', site_design=get_site_design(), registrations=registrations or {})
    except Exception as e:
        flash(f'Error loading registrations: {str(e)}', 'error')
        return render_template('admin/registrations.html', site_design=get_site_design(), registrations={})

@app.route('/admin/registrations/<registration_id>/status', methods=['POST'])
@login_required
@admin_required
def update_registration_status(registration_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['approved', 'rejected']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        # Update registration status in Firebase
        reg_ref = db.reference(f'registrations/{registration_id}')
        registration = reg_ref.get()
        
        if not registration:
            return jsonify({'success': False, 'error': 'Registration not found'}), 404
        
        # Update the status
        reg_ref.update({
            'payment_status': new_status,
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        })
        
        # Send email notification to user
        try:
            msg = Message(
                f'Registration {new_status.title()}',
                recipients=[registration['email']]
            )
            if new_status == 'approved':
                msg.body = f"""
                Dear {registration['full_name']},
                
                Your registration for Conference 2024 has been approved.
                
                Registration Details:
                - Registration Type: {registration['registration_type']}
                - Total Amount: ${registration['total_amount']}
                
                Thank you for registering for our conference.
                
                Best regards,
                Conference Team
                """
            else:
                msg.body = f"""
                Dear {registration['full_name']},
                
                Unfortunately, your registration for Conference 2024 has been rejected.
                
                If you have any questions, please contact us at support@conference2024.com.
                
                Best regards,
                Conference Team
                """
            mail.send(msg)
        except Exception as e:
            print(f"Error sending email: {str(e)}")
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/submissions')
@login_required
@admin_required
def admin_submissions():
    try:
        # Get all submissions from Firebase
        submissions_ref = db.reference('submissions')
        submissions = submissions_ref.get()
        return render_template('admin/submissions.html', site_design=get_site_design(), submissions=submissions or {})
    except Exception as e:
        flash(f'Error loading submissions: {str(e)}', 'error')
        return render_template('admin/submissions.html', site_design=get_site_design(), submissions={})

@app.route('/admin/submissions/<submission_id>/status', methods=['POST'])
@login_required
@admin_required
def update_submission_status(submission_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        comments = data.get('comments', '')
        
        if new_status not in ['accepted', 'rejected', 'revision']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        # Update submission status in Firebase
        sub_ref = db.reference(f'submissions/{submission_id}')
        submission = sub_ref.get()
        
        if not submission:
            return jsonify({'success': False, 'error': 'Submission not found'}), 404
        
        # Update the status and comments
        sub_ref.update({
            'status': new_status,
            'review_comments': comments,
            'updated_at': datetime.now().isoformat(),
            'reviewed_by': current_user.email
        })
        
        # Send email notification to author
        try:
            msg = Message(
                f'Paper Submission {new_status.title()}',
                recipients=[submission['email']]
            )
            
            status_messages = {
                'accepted': """
                Congratulations! Your paper submission has been accepted.
                
                Paper Details:
                Title: {title}
                Category: {category}
                
                Please prepare your camera-ready version following the conference guidelines.
                """,
                'rejected': """
                Thank you for your submission to our conference.
                
                Unfortunately, after careful review, we regret to inform you that your paper was not accepted.
                
                Paper Details:
                Title: {title}
                Category: {category}
                
                We encourage you to consider our feedback for future submissions.
                """,
                'revision': """
                Thank you for your submission to our conference.
                
                Your paper requires revisions before it can be accepted.
                
                Paper Details:
                Title: {title}
                Category: {category}
                
                Review Comments:
                {comments}
                
                Please submit your revised version through the conference system.
                """
            }
            
            msg.body = status_messages[new_status].format(
                title=submission['title'],
                category=submission['category'],
                comments=comments
            )
            
            mail.send(msg)
        except Exception as e:
            print(f"Error sending email: {str(e)}")
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/submissions/<submission_id>/comments', methods=['POST'])
@login_required
@admin_required
def save_submission_comments(submission_id):
    try:
        data = request.get_json()
        comments = data.get('comments', '')
        
        # Update comments in Firebase
        sub_ref = db.reference(f'submissions/{submission_id}')
        submission = sub_ref.get()
        
        if not submission:
            return jsonify({'success': False, 'error': 'Submission not found'}), 404
        
        # Update the comments
        sub_ref.update({
            'review_comments': comments,
            'updated_at': datetime.now().isoformat(),
            'reviewed_by': current_user.email
        })
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/announcements')
@login_required
@admin_required
def admin_announcements():
    try:
        # Get all announcements from Firebase
        announcements_ref = db.reference('announcements')
        announcements = announcements_ref.get()
        
        # Sort announcements by pinned status and date
        if announcements:
            sorted_announcements = dict(sorted(
                announcements.items(),
                key=lambda x: (not x[1].get('is_pinned', False), x[1].get('created_at', '')),
                reverse=True
            ))
        else:
            sorted_announcements = {}
            
        return render_template('admin/announcements.html', site_design=get_site_design(), announcements=sorted_announcements)
    except Exception as e:
        flash(f'Error loading announcements: {str(e)}', 'error')
        return render_template('admin/announcements.html', site_design=get_site_design(), announcements={})

@app.route('/admin/announcements', methods=['POST'])
@login_required
@admin_required
def create_announcement():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'content', 'type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Create new announcement
        announcement = {
            'title': data['title'],
            'content': data['content'],
            'type': data['type'],
            'is_pinned': data.get('is_pinned', False),
            'created_at': datetime.now().isoformat(),
            'created_by': current_user.email,
            'updated_at': datetime.now().isoformat()
        }
        
        # Save to Firebase
        announcements_ref = db.reference('announcements')
        new_announcement = announcements_ref.push(announcement)
        
        # Send email notification for important announcements
        if data['type'] == 'important':
            try:
                # Get all user emails
                users_ref = db.reference('users')
                users = users_ref.get()
                if users:
                    recipient_emails = [user['email'] for user in users.values() if user.get('email')]
                    
                    msg = Message(
                        'Important Conference Announcement',
                        recipients=recipient_emails,
                        body=f"""
                        Important Announcement: {data['title']}
                        
                        {data['content']}
                        
                        Best regards,
                        Conference Team
                        """
                    )
                    mail.send(msg)
            except Exception as e:
                print(f"Error sending email notification: {str(e)}")
        
        return jsonify({'success': True, 'id': new_announcement.key})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/announcements/<announcement_id>', methods=['PUT'])
@login_required
@admin_required
def update_announcement(announcement_id):
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'content', 'type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Update announcement
        announcement_ref = db.reference(f'announcements/{announcement_id}')
        current_announcement = announcement_ref.get()
        
        if not current_announcement:
            return jsonify({'success': False, 'error': 'Announcement not found'}), 404
        
        update_data = {
            'title': data['title'],
            'content': data['content'],
            'type': data['type'],
            'is_pinned': data.get('is_pinned', False),
            'updated_at': datetime.now().isoformat(),
            'updated_by': current_user.email
        }
        
        announcement_ref.update(update_data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        announcement_ref.delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
                'hero_image': DEFAULT_THEME['hero_image']  # Set default initially
            }
            
            # Handle hero image upload
            if 'hero_image' in request.files:
                file = request.files['hero_image']
                if file and file.filename != '' and allowed_image_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    
                    # Create uploads directory if it doesn't exist
                    upload_path = os.path.join(app.static_folder, 'uploads', 'design')
                    os.makedirs(upload_path, exist_ok=True)
                    
                    file_path = os.path.join(upload_path, unique_filename)
                    file.save(file_path)
                    
                    # Update theme data with new image path
                    theme_data['hero_image'] = f"/static/uploads/design/{unique_filename}"
            
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
    downloads_ref = db.reference('downloads')
    downloads = downloads_ref.get()
    return render_template('user/conference/downloads.html', downloads=downloads, site_design=get_site_design())

if __name__ == '__main__':
    create_admin_user()  # Create admin user when starting the app
    app.run(debug=True) 