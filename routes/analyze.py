from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import get_db
from models.profile import get_profile
from models.opportunity import get_opportunity
from models.application import get_applications_for_student
from services.analyzer import analyze_opportunity, analyze_opportunity_manual
from services.pipeline import run_full_analysis
from routes.dashboard import login_required

analyze_bp = Blueprint('analyze', __name__)

@analyze_bp.route('/analyze', methods=['GET'])
@login_required
def analyze_page():
    return render_template('analyze.html', active_page='analyze')

@analyze_bp.route('/analyze', methods=['POST'])
@login_required
def run_analysis():
    user_id = session['user_id']
    db = get_db()
    
    profile = get_profile(db, user_id)
    student_id = profile['id'] if profile else 0
    
    mode = request.form.get('mode', 'paste')
    
    if mode == 'paste':
        text = request.form.get('opportunity_text', '').strip()
        if not text:
            flash('Please paste the opportunity text to analyze.', 'error')
            return redirect(url_for('analyze.analyze_page'))
        extracted = analyze_opportunity(text)
    else:
        manual_data = {
            'title': request.form.get('title', '').strip(),
            'organization': request.form.get('organization', '').strip(),
            'type': request.form.get('type', 'other').strip(),
            'description': request.form.get('description', '').strip(),
            'location': request.form.get('location', '').strip(),
            'remote_onsite': request.form.get('remote_onsite', '').strip(),
            'deadline': request.form.get('deadline', '').strip(),
            'application_url': request.form.get('application_url', '').strip(),
            'eligibility': request.form.get('eligibility', '').strip(),
            'required_skills': request.form.get('required_skills', '').strip(),
            'preferred_skills': request.form.get('preferred_skills', '').strip(),
            'documents': request.form.get('documents', '').strip(),
            'selection_process': request.form.get('selection_process', '').strip(),
        }
        if not manual_data['title']:
            flash('Opportunity title is required for manual entry.', 'error')
            return redirect(url_for('analyze.analyze_page'))
        extracted = analyze_opportunity_manual(manual_data)

    opp_id, final_scores = run_full_analysis(db, user_id, profile, student_id, extracted, source='manual')

    # Render analysis result template
    opportunity = get_opportunity(db, opp_id)
    
    # Check if already tracking
    existing_apps = get_applications_for_student(db, student_id) if student_id else []
    already_saved = any(a['opportunity_id'] == opp_id for a in existing_apps)
    
    return render_template(
        'analysis_result.html',
        active_page='analyze',
        opportunity=opportunity,
        scores=final_scores,
        already_saved=already_saved
    )
