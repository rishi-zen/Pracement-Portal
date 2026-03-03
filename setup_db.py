"""
Programmatic Database Initialization Script
Run this file ONCE to create the SQLite database and Admin user.
"""

from app import app
from models import db, AppUser
from werkzeug.security import generate_password_hash

def initialize_system():
    # Flask requires the app context to execute DB commands
    with app.app_context():
        # Create all tables defined in models.py
        db.create_all()
        
        # Check if an admin account already exists
        existing_admin = AppUser.query.filter_by(account_type='admin').first()
        
        if not existing_admin:
            # Create the pre-existing superuser
            admin_account = AppUser(
                username='admin_iitm',
                pass_hash=generate_password_hash('Admin@2026!'),
                account_type='admin'
            )
            db.session.add(admin_account)
            db.session.commit()
            print("✅ Success: Database created and Admin user (admin_iitm) injected.")
        else:
            print("⚡ Notice: Database already exists and Admin is present.")

if __name__ == '__main__':
    initialize_system()