from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import datetime
import hashlib
import mimetypes
from firebase_admin import db as firebase_db
from utils import get_site_design
import google.generativeai as genai
from config import Config

# Constants
ALLOWED_PAPER_EXTENSIONS = {'pdf', 'doc', 'docx'}
ALLOWED_PAYMENT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
MAX_PAYMENT_PROOF_SIZE = 5 * 1024 * 1024  # 5MB in bytes

# Magic Numbers for file validation
FILE_SIGNATURES = {
    'jpeg': [(0, b'\xFF\xD8\xFF')],  # JPEG/JFIF
    'png': [(0, b'\x89PNG\r\n\x1a\n')],  # PNG
    'pdf': [(0, b'%PDF-')]  # PDF
}

# Create blueprint
user_routes = Blueprint('user', __name__)

def generate_unique_filename(file, user_id):
    """Generate a unique filename based on timestamp, user_id and original filename"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    
    # Create a hash of the original filename
    filename_hash = hashlib.md5(file.filename.encode()).hexdigest()[:8]
    
    return f"{user_id}_{timestamp}_{filename_hash}.{file_extension}"

def ensure_upload_dirs():
    """Ensure upload directories exist"""
    paths = [
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'payments'),
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'papers')
    ]
    for path in paths:
        os.makedirs(path, exist_ok=True)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def check_file_signature(file, file_type):
    """Check if file starts with the expected signature/magic number"""
    if file_type not in FILE_SIGNATURES:
        return False
        
    file.seek(0)
    file_content = file.read(max(len(sig) for offset, sig in FILE_SIGNATURES[file_type]))
    file.seek(0)
    
    # Check all possible signatures for this file type
    for offset, signature in FILE_SIGNATURES[file_type]:
        if file_content[offset:offset + len(signature)] == signature:
            return True
    return False

def validate_file_content(file, allowed_extensions):
    """Validate file content matches its extension"""
    file_ext = file.filename.rsplit('.', 1)[1].lower()
    
    # Map extensions to file types
    ext_to_type = {
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'png': 'png',
        'pdf': 'pdf'
    }
    
    file_type = ext_to_type.get(file_ext)
    if not file_type:
        return False
        
    return check_file_signature(file, file_type)

def save_payment_proof_metadata(user_id, filename, original_filename, file_size):
    """Save payment proof metadata to Firebase"""
    payment_ref = firebase_db.reference(f'payment_proofs/{user_id}')
    metadata = {
        'filename': filename,
        'original_filename': original_filename,
        'file_size': file_size,
        'upload_date': datetime.datetime.now().isoformat(),
        'status': 'pending',
        'mime_type': mimetypes.guess_type(original_filename)[0]
    }
    payment_ref.push(metadata)
    return metadata

def save_registration_to_firebase(registration_data, user_id, payment_metadata):
    """Save registration data to Firebase"""
    # Create registration reference
    registrations_ref = firebase_db.reference('registrations')
    
    # Prepare registration data
    registration_entry = {
        'user_id': user_id,
        'full_name': getattr(current_user, 'full_name', ''),
        'email': getattr(current_user, 'email', ''),
        'institution': getattr(current_user, 'institution', ''),
        'registration_type': registration_data['registration_type'],
        'registration_period': registration_data['registration_period'],
        'payment_proof': registration_data['payment_proof'],
        'payment_notes': registration_data['payment_notes'],
        'payment_status': 'pending',
        'total_amount': registration_data['total_amount'] if 'total_amount' in registration_data else 0,
        'submission_date': registration_data['submission_date'],
        'workshop': registration_data['workshop'],
        'banquet': registration_data['banquet'],
        'extra_paper': registration_data['extra_paper'],
        'payment_metadata': payment_metadata
    }
    
    # If there's a paper, include paper details
    if 'paper' in registration_data and registration_data['paper']:
        registration_entry['paper'] = {
            'filename': registration_data['paper']['filename'],
            'status': 'pending',
            'title': registration_data['paper'].get('title'),
            'presentation_type': registration_data['paper'].get('presentation_type')
        }
    
    # Push the registration data
    new_registration = registrations_ref.push(registration_entry)
    return new_registration.key

@user_routes.route('/registration', methods=['GET', 'POST'])
@login_required
def registration():
    if request.method == 'POST':
        try:
            # Ensure upload directories exist
            ensure_upload_dirs()
            
            # Get form data
            registration_type = request.form.get('registration_type')
            registration_period = request.form.get('registration_period')
            payment_proof = request.files.get('payment_proof')
            paper = request.files.get('paper')
            payment_notes = request.form.get('payment_notes')
            total_amount = request.form.get('total_amount', type=float, default=0)
            
            # Get additional items
            workshop = request.form.get('workshop') == 'true'
            banquet = request.form.get('banquet') == 'true'
            extra_paper = request.form.get('extra_paper') == 'true'

            # Validate required fields
            if not registration_type or not registration_period:
                flash('Please select registration type and period.', 'danger')
                return redirect(url_for('user.registration'))

            # Validate payment proof
            if not payment_proof:
                flash('Please upload a payment proof file.', 'danger')
                return redirect(url_for('user.registration'))
                
            # Check file size
            payment_proof.seek(0, os.SEEK_END)
            size = payment_proof.tell()
            payment_proof.seek(0)
            
            if size > MAX_PAYMENT_PROOF_SIZE:
                flash('Payment proof file is too large. Maximum size is 5MB.', 'danger')
                return redirect(url_for('user.registration'))

            if not allowed_file(payment_proof.filename, ALLOWED_PAYMENT_EXTENSIONS):
                flash('Please upload a valid payment proof file (PDF, JPG, JPEG, PNG).', 'danger')
                return redirect(url_for('user.registration'))
                
            # Validate file content
            if not validate_file_content(payment_proof, ALLOWED_PAYMENT_EXTENSIONS):
                flash('Invalid file content. Please upload a valid file.', 'danger')
                return redirect(url_for('user.registration'))

            # Generate unique filename and save payment proof
            unique_payment_filename = generate_unique_filename(payment_proof, current_user.id)
            payment_proof_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payments', unique_payment_filename)
            payment_proof.save(payment_proof_path)

            # Save payment proof metadata to Firebase
            payment_metadata = save_payment_proof_metadata(
                current_user.id,
                unique_payment_filename,
                payment_proof.filename,
                size
            )

            # Handle paper submission if provided
            paper_data = None
            if paper and allowed_file(paper.filename, ALLOWED_PAPER_EXTENSIONS):
                # Generate unique filename for paper
                paper_filename = generate_unique_filename(paper, current_user.id)
                paper_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'papers', paper_filename)
                paper.save(paper_path)
                paper_data = {
                    'filename': paper_filename,
                    'original_filename': paper.filename,
                    'status': 'pending',
                    'upload_date': datetime.datetime.now().isoformat()
                }

            # Prepare registration data
            registration_data = {
                'user_id': current_user.id,
                'registration_type': registration_type,
                'registration_period': registration_period,
                'payment_proof': unique_payment_filename,
                'payment_notes': payment_notes,
                'status': 'pending',
                'total_amount': total_amount,
                'workshop': workshop,
                'banquet': banquet,
                'extra_paper': extra_paper,
                'payment_metadata': payment_metadata,
                'submission_date': datetime.datetime.now().isoformat(),
                'paper': paper_data
            }

            # Save to Firebase
            registration_id = save_registration_to_firebase(registration_data, current_user.id, payment_metadata)

            flash('Registration submitted successfully! We will review your payment and get back to you.', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            # Clean up saved files if operation fails
            if 'payment_proof_path' in locals():
                try:
                    os.remove(payment_proof_path)
                except:
                    pass
            if 'paper_path' in locals() and paper_data:
                try:
                    os.remove(paper_path)
                except:
                    pass
            flash(f'Error during registration: {str(e)}', 'danger')
            return render_template('user/registration.html', 
                                error=str(e),
                                fees=fees,
                                firebase_config=current_app.config.get('FIREBASE_CONFIG', {}),
                                site_design=get_site_design())
                                
    # GET request - display registration form
    # Get registration fees from Firebase
    fees_ref = firebase_db.reference('registration_fees')
    fees = fees_ref.get()
    
    if not fees:
        fees = {
            'early_bird': {
                'enabled': True,
                'student': 300,
                'regular': 400,
                'end_date': '2024-03-31'
            },
            'regular': {
                'enabled': True,
                'student': 400,
                'regular': 500
            },
            'workshop': 50,
            'banquet': 30,
            'extra_paper': 100
        }
        fees_ref.set(fees)
    
    # Get Firebase config for the template
    firebase_config = current_app.config.get('FIREBASE_CONFIG', {})
    
    return render_template('user/registration.html', 
                         fees=fees,
                         firebase_config=firebase_config,
                         site_design=get_site_design()) 

@user_routes.route('/download/payment_proof/<filename>')
@login_required
def download_payment_proof(filename):
    """Download payment proof file"""
    try:
        # Check if user is admin or if the file belongs to the current user
        if not getattr(current_user, 'is_admin', False):
            # For non-admin users, verify the file belongs to them
            payment_ref = firebase_db.reference(f'payment_proofs/{current_user.id}')
            payments = payment_ref.get()
            if not payments or not any(p.get('filename') == filename for p in payments.values()):
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))

        # Construct the full path to the payment proof
        payment_proof_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payments')
        
        # Check if file exists
        if not os.path.exists(os.path.join(payment_proof_dir, filename)):
            flash('Payment proof file not found.', 'danger')
            return redirect(url_for('dashboard'))
            
        return send_from_directory(
            payment_proof_dir,
            filename,
            as_attachment=True
        )
        
    except Exception as e:
        flash(f'Error downloading payment proof: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@user_routes.route('/download/paper/<filename>')
@login_required
def download_paper(filename):
    """Download paper file"""
    try:
        # Check if user is admin or if the file belongs to the current user
        if not getattr(current_user, 'is_admin', False):
            # For non-admin users, verify the file belongs to them
            registrations_ref = firebase_db.reference('registrations')
            user_registrations = registrations_ref.order_by_child('user_id').equal_to(current_user.id).get()
            if not user_registrations or not any(r.get('paper', {}).get('filename') == filename for r in user_registrations.values()):
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))

        # Construct the full path to the paper
        papers_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'papers')
        
        # Check if file exists
        if not os.path.exists(os.path.join(papers_dir, filename)):
            flash('Paper file not found.', 'danger')
            return redirect(url_for('dashboard'))
            
        return send_from_directory(
            papers_dir,
            filename,
            as_attachment=True
        )
        
    except Exception as e:
        flash(f'Error downloading paper: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@user_routes.route('/api/chat', methods=['POST'])
def chat():
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400

        # Configure Gemini
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')

        # Create context about the GIIP Conference
        context = """
        I am an AI assistant for the GIIP Conference 2024. I can help with:
        - Registration process and fees
        - Paper submission guidelines
        - Conference schedule and venue information
        - Payment methods and deadlines
        - Technical support for the submission system
        
        The conference focuses on academic research and innovation.
        """

        # Generate response using string concatenation
        prompt = context + "\n\nUser: " + message + "\nAssistant:"
        response = model.generate_content(prompt)
        
        return jsonify({
            'response': response.text
        })

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your request'
        }), 500