
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
# Authentication Setup 
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
            # Constraint: Companies must wait for approval 
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
        
        # Create specific profiles 
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
        
        # Pending Approvals 
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
        # Fetch only the drives posted by this specific company 
        my_drives = CampusDrive.query.filter_by(company_ref=current_user.company_record.id).all()
        return render_template('company_dashboard.html', drives=my_drives)
    elif current_user.account_type == 'student':
        # Constraint: View only approved placement drives
        active_drives = CampusDrive.query.filter_by(current_status='Approved').all()
        
        # Fetch the student's complete application history
        my_apps = JobApplication.query.filter_by(student_ref=current_user.student_record.id).all()
        
        # Create a list of drive IDs the student already applied to (to hide the Apply button
        applied_drive_ids = [app.drive_ref for app in my_apps]
        
        return render_template('student_dashboard.html', 
                               drives=active_drives, 
                               applications=my_apps,
                               applied_ids=applied_drive_ids)

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
# ==========================================
# Company Functionalities 
# ==========================================
from datetime import datetime

@app.route('/company/post_drive', methods=['POST'])
@login_required
def post_drive():
    if current_user.account_type != 'company':
        return redirect(url_for('dashboard_route'))
        
    # Combine skills, experience, and salary to fit within our DB schema
    deadline_str = request.form.get('deadline')
    deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
    
    new_drive = CampusDrive(
        company_ref=current_user.company_record.id,
        role_title=request.form.get('job_title'),
        role_desc=f"{request.form.get('job_desc')} | Salary: {request.form.get('salary')}",
        requirements=f"Skills: {request.form.get('skills')} | Exp: {request.form.get('experience')}",
        last_date=deadline_date,
        current_status='Pending' # Requires Admin Approval 
    )
    db.session.add(new_drive)
    db.session.commit()
    flash('New Job Posting submitted! Awaiting Admin approval.', 'info')
    return redirect(url_for('dashboard_route'))

@app.route('/company/update_drive/<int:drive_id>', methods=['POST'])
@login_required
def update_drive(drive_id):
    if current_user.account_type != 'company':
        return redirect(url_for('dashboard_route'))
        
    drive = CampusDrive.query.get_or_404(drive_id)
    # Ensure this company owns the drive
    if drive.company_ref == current_user.company_record.id:
        drive.current_status = request.form.get('new_status') # e.g., 'Closed' 
        db.session.commit()
        flash(f'Drive status updated to {drive.current_status}.', 'success')
    return redirect(url_for('dashboard_route'))

@app.route('/company/update_app/<int:app_id>', methods=['POST'])
@login_required
def update_application(app_id):
    if current_user.account_type != 'company':
        return redirect(url_for('dashboard_route'))
        
    application = JobApplication.query.get_or_404(app_id)
    # Ensure this application belongs to a drive owned by this company
    if application.drive_details.company_ref == current_user.company_record.id:
        # Update selection status (Shortlisted / Selected / Rejected) 
        application.selection_status = request.form.get('new_status') 
        db.session.commit()
        flash('Applicant status updated.', 'success')
    return redirect(url_for('dashboard_route'))
# ==========================================
# Student Functionalities
# ==========================================
@app.route('/student/apply/<int:drive_id>', methods=['POST'])
@login_required
def apply_for_drive(drive_id):
    if current_user.account_type != 'student':
        return redirect(url_for('dashboard_route'))
        
    student_id = current_user.student_record.id
    
    # Constraint: Prevent duplicate job applications for the same posting [cite: 128, 486-488]
    existing_app = JobApplication.query.filter_by(student_ref=student_id, drive_ref=drive_id).first()
    if existing_app:
        flash('You have already applied for this placement drive.', 'warning')
        return redirect(url_for('dashboard_route'))
        
    new_application = JobApplication(
        student_ref=student_id,
        drive_ref=drive_id,
        selection_status='Applied' # Default status 
    )
    db.session.add(new_application)
    db.session.commit()
    
    flash('Successfully applied to the placement drive!', 'success')
    return redirect(url_for('dashboard_route'))

if __name__ == '__main__':
    app.run(debug=True)
    