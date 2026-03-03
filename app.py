"""
Main Application Logic
Author: Rishi Kumar Singh
Course: MAD-I
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, AppUser, CompanyProfile, StudentProfile
from models import db, AppUser, CompanyProfile, StudentProfile, CampusDrive, JobApplication

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rishi_madi_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ==========================================
# Authentication Setup [cite: 181-184, 498]
# ==========================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_route'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return AppUser.query.get(int(user_id))

# ==========================================
# Core Routes
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        form_username = request.form.get('username')
        form_password = request.form.get('password')
        
        user = AppUser.query.filter_by(username=form_username).first()
        
        if user and check_password_hash(user.pass_hash, form_password):
            # Constraint: Companies must wait for approval [cite: 66, 366-367]
            if user.account_type == 'company':
                if user.company_record.admin_verification != 'Approved':
                    flash('Access Denied: Your company profile is pending Admin approval.', 'danger')
                    return redirect(url_for('login_route'))
            
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard_route'))
            
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register_route():
    if request.method == 'POST':
        role = request.form.get('role_type') # 'student' or 'company'
        username = request.form.get('username')
        password = request.form.get('password')
        
        if AppUser.query.filter_by(username=username).first():
            flash('Username is already taken.', 'warning')
            return redirect(url_for('register_route'))
            
        # Create base user
        new_user = AppUser(
            username=username, 
            pass_hash=generate_password_hash(password), 
            account_type=role
        )
        db.session.add(new_user)
        db.session.flush() # Get the ID before committing
        
        # Create specific profiles [cite: 58-59, 108-111, 463-464]
        if role == 'student':
            student = StudentProfile(
                auth_id=new_user.id,
                candidate_name=request.form.get('full_name'),
                degree_info=request.form.get('education')
            )
            db.session.add(student)
            flash('Student account created! You can now log in.', 'success')
            
        elif role == 'company':
            company = CompanyProfile(
                auth_id=new_user.id,
                org_name=request.form.get('company_name'),
                business_sector=request.form.get('industry'),
                hr_email=request.form.get('hr_contact'),
                admin_verification='Pending'
            )
            db.session.add(company)
            flash('Company registered! Awaiting Admin approval.', 'info')
            
        db.session.commit()
        return redirect(url_for('login_route'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout_route():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard_route():
    if current_user.account_type == 'admin':
        # Admin Stats 
        t_students = StudentProfile.query.count()
        t_companies = CompanyProfile.query.count()
        t_drives = CampusDrive.query.count()
        t_apps = JobApplication.query.count()
        
        # Pending Approvals [cite: 66, 348-354]
        pending_comps = CompanyProfile.query.filter_by(admin_verification='Pending').all()
        pending_drives = CampusDrive.query.filter_by(current_status='Pending').all()
        
        return render_template('admin_dashboard.html', 
                               t_students=t_students, 
                               t_companies=t_companies, 
                               t_drives=t_drives, 
                               t_apps=t_apps,
                               p_comps=pending_comps, 
                               p_drives=pending_drives)
                               
    elif current_user.account_type == 'company':
        return render_template('company_dashboard.html')
    else:
        return render_template('student_dashboard.html')


@app.route('/admin/verify_company/<int:comp_id>', methods=['POST'])
@login_required
def verify_company(comp_id):
    if current_user.account_type != 'admin':
        return redirect(url_for('dashboard_route'))
    
    action = request.form.get('action_type') # 'Approve' or 'Reject'
    company = CompanyProfile.query.get_or_404(comp_id)
    
    company.admin_verification = 'Approved' if action == 'Approve' else 'Rejected'
    db.session.commit()
    
    flash(f"Company {company.org_name} has been {company.admin_verification}.", 'success')
    return redirect(url_for('dashboard_route'))

@app.route('/admin/verify_drive/<int:drive_id>', methods=['POST'])
@login_required
def verify_drive(drive_id):
    if current_user.account_type != 'admin':
        return redirect(url_for('dashboard_route'))
        
    action = request.form.get('action_type')
    drive = CampusDrive.query.get_or_404(drive_id)
    
    drive.current_status = 'Approved' if action == 'Approve' else 'Rejected'
    db.session.commit()
    
    flash(f"Placement Drive '{drive.role_title}' has been {drive.current_status}.", 'success')
    return redirect(url_for('dashboard_route'))

if __name__ == '__main__':
    app.run(debug=True)