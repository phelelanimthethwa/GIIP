from flask import Flask, render_template, request, redirect, url_for, flash
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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/call-for-papers')
def call_for_papers():
    return render_template('call_for_papers.html')

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

    return render_template('paper_submission.html', recaptcha_site_key=app.config['RECAPTCHA_SITE_KEY'])

@app.route('/author-guidelines')
def author_guidelines():
    return render_template('author_guidelines.html')

@app.route('/venue')
def venue():
    # Get venue details from Firebase
    venue_ref = db.reference('venue')
    venue_details = venue_ref.get()
    return render_template('venue.html', venue_details=venue_details)

@app.route('/video-conference')
def video_conference():
    return render_template('video_conference.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

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
    return render_template('login.html')

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
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

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
            return render_template('register.html')
    
    return render_template('register.html')

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
    
    return render_template('registration.html', fees=fees)

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user's registrations from Firebase
        ref = db.reference('registrations')
        registrations = ref.order_by_child('email').equal_to(current_user.email).get()
        return render_template('dashboard.html', registrations=registrations or {})
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', registrations={})

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
    return render_template('admin_venue.html', venue_details=venue_details)

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
    return render_template('admin_registration_fees.html', fees=fees)

if __name__ == '__main__':
    create_admin_user()  # Create admin user when starting the app
    app.run(debug=True) 