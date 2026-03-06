from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ==========================================================
# Core Authentication Model
# ==========================================================
class AppUser(UserMixin, db.Model):
    __tablename__ = 'app_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    pass_hash = db.Column(db.String(256), nullable=False)
    account_type = db.Column(db.String(20), nullable=False) # Roles: admin, company, student
    
    # One-to-One links to role-specific profiles
    student_record = db.relationship('StudentProfile', backref='linked_account', uselist=False)
    company_record = db.relationship('CompanyProfile', backref='linked_account', uselist=False)

# ==========================================================
# Company Profile Model
# ==========================================================
class CompanyProfile(db.Model):
    __tablename__ = 'company_profiles'
    
    id = db.Column(db.Integer, primary_key=True) 
    auth_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False)
    
    # Required company details
    org_name = db.Column(db.String(150), nullable=False)
    business_sector = db.Column(db.String(100)) 
    hr_email = db.Column(db.String(100))
    company_url = db.Column(db.String(150))
    
    # Admin approval control
    admin_verification = db.Column(db.String(20), default='Pending') # Pending / Approved / Rejected
    
    # Link to the drives they post
    drives_posted = db.relationship('CampusDrive', backref='recruiter', lazy=True)

# ==========================================================
# Student Profile Model
# ==========================================================
class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'
    
    id = db.Column(db.Integer, primary_key=True) 
    auth_id = db.Column(db.Integer, db.ForeignKey('app_users.id'), nullable=False)
    
    # Candidate details
    candidate_name = db.Column(db.String(150), nullable=False)
    degree_info = db.Column(db.String(200))
    core_skills = db.Column(db.String(300))
    cv_file_path = db.Column(db.String(300))
    
    # Link to applications they submit
    jobs_applied = db.relationship('JobApplication', backref='applicant', lazy=True)

# ==========================================================
# Placement Drive / Job Posting Model
# ==========================================================
class CampusDrive(db.Model):
    __tablename__ = 'campus_drives'
    
    id = db.Column(db.Integer, primary_key=True) 
    company_ref = db.Column(db.Integer, db.ForeignKey('company_profiles.id'), nullable=False)
    

    role_title = db.Column(db.String(150), nullable=False)
    role_desc = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    last_date = db.Column(db.Date, nullable=False)
    
    # Drive status
    current_status = db.Column(db.String(20), default='Pending') # Pending / Approved / Closed
    
    # Link to received applications
    received_applications = db.relationship('JobApplication', backref='drive_details', lazy=True)

# ==========================================================
# Student Application Record Model
# ==========================================================
class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    
    id = db.Column(db.Integer, primary_key=True) 
    student_ref = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    drive_ref = db.Column(db.Integer, db.ForeignKey('campus_drives.id'), nullable=False)
    
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Selection status
    selection_status = db.Column(db.String(20), default='Applied') # Applied / Shortlisted / Selected / Rejected