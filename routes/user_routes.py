from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from models.registration import Registration, Paper
from models import db
from firebase_admin import db as firebase_db
from utils import get_site_design

# Define allowed file extensions
ALLOWED_PAPER_EXTENSIONS = {'pdf', 'doc', 'docx'}
ALLOWED_PAYMENT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

# Create blueprint
user_routes = Blueprint('user', __name__)

@user_routes.route('/registration', methods=['GET', 'POST'])
@login_required
def registration():
    if request.method == 'POST':
        try:
            # Get form data
            registration_type = request.form.get('registration_type')
            registration_period = request.form.get('registration_period')
            payment_proof = request.files.get('payment_proof')
            paper = request.files.get('paper')
            payment_notes = request.form.get('payment_notes')

            # Validate required fields
            if not registration_type or not registration_period:
                flash('Please select registration type and period.', 'danger')
                return redirect(url_for('user.registration'))

            # Validate payment proof
            if not payment_proof or not allowed_file(payment_proof.filename, ALLOWED_PAYMENT_EXTENSIONS):
                flash('Please upload a valid payment proof file (PDF, JPG, JPEG, PNG).', 'danger')
                return redirect(url_for('user.registration'))

            # Save payment proof
            payment_proof_filename = secure_filename(payment_proof.filename)
            payment_proof_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payments', payment_proof_filename)
            payment_proof.save(payment_proof_path)

            # Handle paper submission if provided
            paper_filename = None
            if paper and allowed_file(paper.filename, ALLOWED_PAPER_EXTENSIONS):
                paper_filename = secure_filename(paper.filename)
                paper_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'papers', paper_filename)
                paper.save(paper_path)

            # Create registration record
            registration = Registration(
                user_id=current_user.id,
                registration_type=registration_type,
                registration_period=registration_period,
                payment_proof=payment_proof_filename,
                payment_notes=payment_notes,
                status='pending'
            )

            # Create paper record if paper was submitted
            if paper_filename:
                paper_record = Paper(
                    filename=paper_filename,
                    status='pending'
                )
                registration.paper = paper_record

            # Save to database
            db.session.add(registration)
            db.session.commit()

            flash('Registration submitted successfully! We will review your payment and get back to you.', 'success')
            return redirect(url_for('user.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error during registration: {str(e)}', 'danger')
            return render_template('user/registration.html', 
                                selected_type=request.form.get('registration_type'),
                                selected_period=request.form.get('registration_period'))

    # GET request - show registration page
    # Get registration fees from Firebase
    fees_ref = firebase_db.reference('registration_fees')
    fees = fees_ref.get()
    
    # Get Firebase config from Config
    firebase_config = current_app.config['FIREBASE_CONFIG']
    
    return render_template('user/registration.html',
                         fees=fees,
                         firebase_config=firebase_config,
                         site_design=get_site_design())

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions 