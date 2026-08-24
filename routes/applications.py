from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from database.db import get_db
from models.profile import get_profile
from models.application import (
    create_application, get_application, get_application_by_opportunity, get_applications_for_student,
    update_application_status, update_application_notes,
    get_tasks, toggle_task, delete_application, generate_checklist_from_opportunity
)
from routes.dashboard import login_required

applications_bp = Blueprint('applications', __name__)

@applications_bp.route('/applications')
@login_required
def applications_page():
    user_id = session['user_id']
    db = get_db()
    
    profile = get_profile(db, user_id)
    student_id = profile['id'] if profile else 0
    
    current_status = request.args.get('status', '').strip()
    apps = get_applications_for_student(db, student_id, status_filter=current_status if current_status else None)
    
    return render_template(
        'applications.html',
        active_page='applications',
        applications=apps,
        current_status=current_status
    )

@applications_bp.route('/application/save/<int:opportunity_id>', methods=['POST'])
@login_required
def save_application(opportunity_id):
    user_id = session['user_id']
    db = get_db()
    
    profile = get_profile(db, user_id)
    student_id = profile['id'] if profile else 0
    
    existing = get_application_by_opportunity(db, student_id, opportunity_id) if student_id else None
    if existing:
        flash('You are already tracking this opportunity.', 'info')
        return redirect(url_for('applications.application_detail', application_id=existing['id']))
    
    app_id = create_application(db, student_id, opportunity_id)
    generate_checklist_from_opportunity(db, app_id, opportunity_id)
    db.commit()
    
    flash('Application added to your tracker with interactive checklist!', 'success')
    return redirect(url_for('applications.application_detail', application_id=app_id))

@applications_bp.route('/application/<int:application_id>')
@login_required
def application_detail(application_id):
    db = get_db()
    app_data = get_application(db, application_id)
    if not app_data:
        flash('Application not found.', 'error')
        return redirect(url_for('applications.applications_page'))
        
    tasks = get_tasks(db, application_id)
    
    return render_template(
        'application_detail.html',
        active_page='applications',
        app_data=app_data,
        tasks=tasks
    )

@applications_bp.route('/application/<int:application_id>/status', methods=['POST'])
@login_required
def update_status(application_id):
    db = get_db()
    new_status = request.json.get('status') if request.is_json else request.form.get('status')
    
    if new_status:
        update_application_status(db, application_id, new_status)
        db.commit()
        if request.is_json:
            return jsonify({'status': 'success', 'new_status': new_status})
        flash(f'Status updated to {new_status.title()}.', 'success')
        
    if request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid status'}), 400
    return redirect(url_for('applications.application_detail', application_id=application_id))

@applications_bp.route('/application/<int:application_id>/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task_route(application_id, task_id):
    db = get_db()
    new_state = toggle_task(db, task_id)
    db.commit()
    
    tasks = get_tasks(db, application_id)
    done_count = sum(1 for t in tasks if t['completed'])
    total_count = len(tasks)
    
    if request.is_json:
        return jsonify({
            'status': 'success',
            'completed': new_state,
            'done_count': done_count,
            'total_count': total_count
        })
        
    return redirect(url_for('applications.application_detail', application_id=application_id))

@applications_bp.route('/application/<int:application_id>/notes', methods=['POST'])
@login_required
def update_notes(application_id):
    db = get_db()
    notes = request.form.get('notes', '').strip()
    update_application_notes(db, application_id, notes)
    db.commit()
    flash('Notes saved.', 'success')
    return redirect(url_for('applications.application_detail', application_id=application_id))

@applications_bp.route('/application/<int:application_id>/delete', methods=['POST'])
@login_required
def delete_application_route(application_id):
    db = get_db()
    delete_application(db, application_id)
    db.commit()
    flash('Application tracking removed.', 'info')
    return redirect(url_for('applications.applications_page'))
