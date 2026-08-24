from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from database.db import get_db
from models.profile import (
    get_profile, update_profile, add_skill, remove_skill,
    add_interest, remove_interest, add_preference, remove_preference,
    get_all_skills, get_all_interests, get_all_preferences
)
from routes.dashboard import login_required

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
@login_required
def profile_page():
    user_id = session['user_id']
    db = get_db()
    
    profile = get_profile(db, user_id)
    skills = profile.get('skills', []) if profile else []
    interests = profile.get('interests', []) if profile else []
    preferences = profile.get('preferences', {'types': [], 'formats': []}) if profile else {'types': [], 'formats': []}
    
    all_skills = get_all_skills(db)
    all_interests = get_all_interests(db)
    
    return render_template(
        'profile.html',
        active_page='profile',
        profile=profile,
        skills=skills,
        interests=interests,
        preferences=preferences,
        all_skills=all_skills,
        all_interests=all_interests
    )

@profile_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile_route():
    user_id = session['user_id']
    db = get_db()
    
    data = {
        'university': request.form.get('university', '').strip(),
        'degree': request.form.get('degree', '').strip(),
        'major': request.form.get('major', '').strip(),
        'semester': int(request.form.get('semester', 1) or 1),
        'cgpa': float(request.form.get('cgpa', 0.0) or 0.0),
        'graduation_year': int(request.form.get('graduation_year', 2026) or 2026),
        'location': request.form.get('location', '').strip(),
        'coursework': request.form.get('coursework', '').strip(),
        'experience': request.form.get('experience', '').strip(),
    }
    
    update_profile(db, user_id, data)
    db.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile.profile_page'))

@profile_bp.route('/profile/skill/add', methods=['POST'])
@login_required
def add_skill_route():
    user_id = session['user_id']
    db = get_db()
    profile = get_profile(db, user_id)
    
    skill_name = request.json.get('name') if request.is_json else request.form.get('name')
    if skill_name and profile:
        add_skill(db, profile['id'], skill_name.strip())
        db.commit()
        if request.is_json:
            return jsonify({'status': 'success', 'name': skill_name})
        flash(f'Skill "{skill_name}" added.', 'success')
        
    if request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    return redirect(url_for('profile.profile_page'))

@profile_bp.route('/profile/skill/remove', methods=['POST'])
@login_required
def remove_skill_route():
    user_id = session['user_id']
    db = get_db()
    profile = get_profile(db, user_id)
    
    skill_name = request.json.get('name') if request.is_json else request.form.get('name')
    if skill_name and profile:
        remove_skill(db, profile['id'], skill_name.strip())
        db.commit()
        if request.is_json:
            return jsonify({'status': 'success', 'name': skill_name})
            
    if request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    return redirect(url_for('profile.profile_page'))

@profile_bp.route('/profile/interest/add', methods=['POST'])
@login_required
def add_interest_route():
    user_id = session['user_id']
    db = get_db()
    profile = get_profile(db, user_id)
    
    interest_name = request.json.get('name') if request.is_json else request.form.get('name')
    if interest_name and profile:
        add_interest(db, profile['id'], interest_name.strip())
        db.commit()
        if request.is_json:
            return jsonify({'status': 'success', 'name': interest_name})
            
    if request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    return redirect(url_for('profile.profile_page'))

@profile_bp.route('/profile/interest/remove', methods=['POST'])
@login_required
def remove_interest_route():
    user_id = session['user_id']
    db = get_db()
    profile = get_profile(db, user_id)
    
    interest_name = request.json.get('name') if request.is_json else request.form.get('name')
    if interest_name and profile:
        remove_interest(db, profile['id'], interest_name.strip())
        db.commit()
        if request.is_json:
            return jsonify({'status': 'success', 'name': interest_name})
            
    if request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    return redirect(url_for('profile.profile_page'))

@profile_bp.route('/profile/preference/toggle', methods=['POST'])
@login_required
def toggle_preference_route():
    user_id = session['user_id']
    db = get_db()
    profile = get_profile(db, user_id)
    
    pref_name = request.json.get('name') if request.is_json else request.form.get('name')
    action = request.json.get('action') if request.is_json else request.form.get('action')
    
    if pref_name and profile:
        if action == 'remove':
            remove_preference(db, profile['id'], pref_name.strip())
        else:
            add_preference(db, profile['id'], pref_name.strip())
        db.commit()
        if request.is_json:
            return jsonify({'status': 'success', 'name': pref_name})
            
    if request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400
    return redirect(url_for('profile.profile_page'))
