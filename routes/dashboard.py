from flask import Blueprint, render_template, session, redirect, url_for
from database.db import get_db
from models.profile import get_profile
from models.opportunity import get_dashboard_data
from models.application import get_applications_for_student
from models.gmail import get_gmail_account, count_pending_synced_opportunities
from routes.decorators import login_required  # re-exported for existing imports

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def dashboard_page():
    user_id = session['user_id']
    db = get_db()
    
    profile = get_profile(db, user_id)
    student_id = profile['id'] if profile else 0
    
    dash_data = get_dashboard_data(db, user_id, student_id)
    recent_apps = get_applications_for_student(db, student_id) if student_id else []

    gmail_account = get_gmail_account(db, user_id)
    inbox_pending_count = count_pending_synced_opportunities(db, user_id)
    
    profile_complete = False
    if profile and profile.get('university') and profile.get('degree') and profile.get('skills'):
        profile_complete = True

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        stats=dash_data['stats'],
        high_priority=dash_data['high_priority'],
        recent_applications=recent_apps,
        profile_complete=profile_complete,
        gmail_account=gmail_account,
        inbox_pending_count=inbox_pending_count
    )
