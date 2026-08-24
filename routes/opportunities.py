from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import get_db
from models.profile import get_profile
from models.opportunity import get_opportunities_for_user, get_opportunity, get_scores, delete_opportunity
from models.application import get_applications_for_student
from routes.dashboard import login_required

opportunities_bp = Blueprint('opportunities', __name__)

@opportunities_bp.route('/opportunities')
@login_required
def opportunities_page():
    user_id = session['user_id']
    db = get_db()
    
    current_type = request.args.get('type', '').strip()
    current_search = request.args.get('search', '').strip()
    current_sort = request.args.get('sort', 'match').strip()
    
    filters = {}
    if current_type:
        filters['type'] = current_type
    if current_search:
        filters['search'] = current_search

    profile = get_profile(db, user_id)
    student_id = profile['id'] if profile else 0

    opps = get_opportunities_for_user(db, user_id, filters, student_id=student_id)
    
    # Sorting in Python if needed
    if current_sort == 'match':
        opps = sorted(opps, key=lambda x: x.get('match_score') or 0, reverse=True)
    elif current_sort == 'urgency':
        opps = sorted(opps, key=lambda x: x.get('urgency_score') or 0, reverse=True)
    elif current_sort == 'trust':
        opps = sorted(opps, key=lambda x: x.get('trust_score') or 0, reverse=True)
    elif current_sort == 'newest':
        opps = sorted(opps, key=lambda x: x.get('id') or 0, reverse=True)

    return render_template(
        'opportunities.html',
        active_page='opportunities',
        opportunities=opps,
        current_type=current_type,
        current_search=current_search,
        current_sort=current_sort
    )

@opportunities_bp.route('/opportunity/<int:opportunity_id>')
@login_required
def opportunity_detail(opportunity_id):
    user_id = session['user_id']
    db = get_db()
    
    opp = get_opportunity(db, opportunity_id)
    if not opp:
        flash('Opportunity not found.', 'error')
        return redirect(url_for('opportunities.opportunities_page'))

    # Removed opportunities are hidden from normal student browsing, but
    # admins still need to open them (e.g. from the moderation queue) to
    # review what was removed.
    if opp.get('moderation_status') == 'removed' and session.get('role') != 'admin':
        flash('Opportunity not found.', 'error')
        return redirect(url_for('opportunities.opportunities_page'))
        
    profile = get_profile(db, user_id)
    student_id = profile['id'] if profile else 0
    scores = get_scores(db, opportunity_id, student_id) if student_id else None
    
    existing_apps = get_applications_for_student(db, student_id) if student_id else []
    already_tracking = any(a['opportunity_id'] == opportunity_id for a in existing_apps)

    return render_template(
        'opportunity_detail.html',
        active_page='opportunities',
        opportunity=opp,
        scores=scores,
        already_tracking=already_tracking
    )

@opportunities_bp.route('/opportunity/<int:opportunity_id>/delete', methods=['POST'])
@login_required
def delete_opportunity_route(opportunity_id):
    user_id = session['user_id']
    db = get_db()
    
    opp = get_opportunity(db, opportunity_id)
    if opp and opp.get('user_id') == user_id:
        delete_opportunity(db, opportunity_id)
        db.commit()
        flash('Opportunity deleted.', 'info')
    
    return redirect(url_for('opportunities.opportunities_page'))
