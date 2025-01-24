from datetime import datetime
from . import db

class Registration(db.Model):
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    institution = db.Column(db.String(200), nullable=False)
    registration_type = db.Column(db.String(50), nullable=False)
    registration_period = db.Column(db.String(50), nullable=False)
    registration_fee = db.Column(db.Float, nullable=False)
    workshop = db.Column(db.Boolean, default=False)
    banquet = db.Column(db.Boolean, default=False)
    payment_proof_path = db.Column(db.String(255))
    payment_reference = db.Column(db.String(100))
    total_amount = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with Paper model for authors
    paper = db.relationship('Paper', backref='registration', uselist=False)

    def __repr__(self):
        return f'<Registration {self.full_name}>'

class Paper(db.Model):
    __tablename__ = 'papers'

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    abstract = db.Column(db.Text, nullable=False)
    presentation_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Paper {self.title}>' 