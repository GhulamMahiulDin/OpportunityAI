from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import get_db
from models.user import create_user, get_user_by_email, verify_password, get_user_by_id
from models.admin import log_login_attempt, record_login

auth_bp = Blueprint('auth', __name__)


def _home_for_role(role):
    """Where a logged-in user should land: admins go to the admin
    dashboard, students go to their normal dashboard."""
    if role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    return redirect(url_for('dashboard.dashboard_page'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        db = get_db()
        current = get_user_by_id(db, session['user_id'])
        return _home_for_role(current.get('role') if current else session.get('role'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = 'Please provide both email and password.'
        else:
            db = get_db()
            user = get_user_by_email(db, email)
            if user and not user.get('password_hash'):
                error = 'This account uses Google Sign-In. Please continue with Google below.'
            elif user and not user.get('is_active', 1):
                error = 'This account has been deactivated. Contact an administrator.'
                log_login_attempt(db, email, success=False, user_id=user['id'], ip_address=request.remote_addr or '')
            elif user and verify_password(user['password_hash'], password):
                session.clear()
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                session['role'] = user.get('role', 'student')
                record_login(db, user['id'])
                log_login_attempt(db, email, success=True, user_id=user['id'], ip_address=request.remote_addr or '')
                flash(f"Welcome back, {user['name']}!", 'success')
                return _home_for_role(user.get('role'))
            else:
                error = 'Invalid email or password.'
                log_login_attempt(db, email, success=False, user_id=user['id'] if user else None, ip_address=request.remote_addr or '')

    return render_template('login.html', error=error)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        db = get_db()
        current = get_user_by_id(db, session['user_id'])
        return _home_for_role(current.get('role') if current else session.get('role'))

    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password:
            error = 'All fields are required.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters long.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        else:
            db = get_db()
            existing = get_user_by_email(db, email)
            if existing:
                error = 'An account with this email already exists.'
            else:
                user_id = create_user(db, name, email, password)
                db.commit()
                user = get_user_by_email(db, email)
                session.clear()
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                session['role'] = user.get('role', 'student')
                record_login(db, user['id'])
                flash('Account created successfully! Please complete your profile.', 'success')
                return redirect(url_for('profile.profile_page'))

    return render_template('register.html', error=error)

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@auth_bp.route('/terms')
def terms():
    return render_template('terms.html')

@auth_bp.route('/google-verification')
def google_verification():
    return render_template('google_verification.html')
