from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import get_db
from routes.decorators import admin_required, super_admin_required
from models.admin import (
    get_system_stats, get_all_users, get_user_admin_detail,
    set_user_active_status, set_user_role,
    get_opportunities_for_moderation, set_opportunity_moderation_status,
    correct_opportunity_field, log_admin_action,
    get_recent_admin_activity, get_recent_login_activity,
    log_login_attempt, record_login
)
from models.user import get_user_by_id, get_user_by_email, verify_password
from services.authz import is_super_admin
from services.pipeline import rescore_opportunity_for_all_students
from config import Config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """
    Separate admin login portal. Any user can submit credentials here,
    but only an account whose DATABASE role is 'admin' is let in — a
    valid student login is rejected with an explicit access-denied
    message rather than silently starting a student session.
    """
    if 'user_id' in session:
        db = get_db()
        current = get_user_by_id(db, session['user_id'])
        if current and current.get('role') == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('dashboard.dashboard_page'))

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
                error = 'This account uses Google Sign-In. Please use the regular login page.'
            elif user and not user.get('is_active', 1):
                error = 'This account has been deactivated. Contact the Super Admin.'
                log_login_attempt(db, email, success=False, user_id=user['id'], ip_address=request.remote_addr or '')
            elif user and verify_password(user['password_hash'], password):
                if user.get('role') != 'admin':
                    error = 'Access denied. This portal is for administrators only.'
                    log_login_attempt(db, email, success=False, user_id=user['id'], ip_address=request.remote_addr or '')
                else:
                    session.clear()
                    session['user_id'] = user['id']
                    session['user_name'] = user['name']
                    session['user_email'] = user['email']
                    session['role'] = user.get('role', 'student')
                    record_login(db, user['id'])
                    log_login_attempt(db, email, success=True, user_id=user['id'], ip_address=request.remote_addr or '')
                    flash(f"Welcome back, {user['name']}!", 'success')
                    return redirect(url_for('admin.admin_dashboard'))
            else:
                error = 'Invalid email or password.'
                log_login_attempt(db, email, success=False, user_id=user['id'] if user else None, ip_address=request.remote_addr or '')

    return render_template('admin/login.html', error=error)


@admin_bp.route('/')
@admin_required
def admin_dashboard():
    db = get_db()
    stats = get_system_stats(db)
    recent_activity, _ = get_recent_admin_activity(db, limit=10)
    recent_logins, _ = get_recent_login_activity(db, limit=10)
    return render_template(
        'admin/dashboard.html',
        active_page='admin',
        stats=stats,
        recent_activity=recent_activity,
        recent_logins=recent_logins
    )


USERS_PER_PAGE = 25


@admin_bp.route('/users')
@admin_required
def users_list():
    db = get_db()
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    users, total_count = get_all_users(
        db, search=search or None, role_filter=role_filter or None,
        page=page, per_page=USERS_PER_PAGE
    )
    total_pages = max(1, (total_count + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    # If a stale/out-of-range page is requested (e.g. filters just
    # narrowed the result set), keep the user on the last real page
    # instead of silently rendering an empty list.
    if page > total_pages:
        page = total_pages
        users, total_count = get_all_users(
            db, search=search or None, role_filter=role_filter or None,
            page=page, per_page=USERS_PER_PAGE
        )

    return render_template(
        'admin/users.html',
        active_page='admin',
        users=users,
        search=search,
        role_filter=role_filter,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        super_admin_email=Config.SUPER_ADMIN_EMAIL
    )


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    db = get_db()
    user = get_user_admin_detail(db, user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users_list'))
    current_user = get_user_by_id(db, session['user_id'])
    return render_template(
        'admin/user_detail.html',
        active_page='admin',
        user=user,
        target_is_super_admin=is_super_admin(user),
        viewer_is_super_admin=is_super_admin(current_user)
    )


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    db = get_db()
    if user_id == session['user_id']:
        flash("You can't deactivate your own account.", 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    target = get_user_by_id(db, user_id)
    if not target:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users_list'))

    new_status = not target.get('is_active', 1)
    try:
        set_user_active_status(db, user_id, new_status)
    except PermissionError as e:
        flash(str(e), 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    except LookupError:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users_list'))

    log_admin_action(
        db, session['user_id'],
        action='ACTIVATE_USER' if new_status else 'DEACTIVATE_USER',
        target_type='user', target_id=user_id,
        details=f"{'Activated' if new_status else 'Deactivated'} {target['email']}"
    )
    flash(f"{target['name']} has been {'activated' if new_status else 'deactivated'}.", 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@super_admin_required
def change_user_role(user_id):
    """
    Grants or removes administrator privileges. Restricted to the Super
    Admin only (see super_admin_required) — this keeps administrator
    privilege management centralized to a single account rather than
    letting any promoted admin promote/demote others.
    """
    db = get_db()
    new_role = request.form.get('role', '').strip()

    if user_id == session['user_id'] and new_role != 'admin':
        flash("You can't remove your own admin access.", 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))

    target = get_user_by_id(db, user_id)
    if not target:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users_list'))

    previous_role = target.get('role')

    try:
        set_user_role(db, user_id, new_role)
    except ValueError:
        flash('Invalid role.', 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    except PermissionError as e:
        flash(str(e), 'error')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    except LookupError:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users_list'))

    action = 'ADMIN_ROLE_GRANTED' if new_role == 'admin' else 'ADMIN_ROLE_REMOVED'
    log_admin_action(
        db, session['user_id'], action=action,
        target_type='user', target_id=user_id,
        details=f"{target['email']}: role changed from {previous_role} to {new_role}"
    )
    flash(f"{target['name']}'s role changed to {new_role}.", 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))


OPPS_PER_PAGE = 20


@admin_bp.route('/opportunities')
@admin_required
def opportunities_moderation():
    db = get_db()
    status_filter = request.args.get('status', '').strip()
    try:
        page = max(1, int(request.args.get('page', 1)))
    except ValueError:
        page = 1

    opportunities, total_count = get_opportunities_for_moderation(
        db, status_filter=status_filter or None, page=page, per_page=OPPS_PER_PAGE
    )
    total_pages = max(1, (total_count + OPPS_PER_PAGE - 1) // OPPS_PER_PAGE)
    if page > total_pages:
        page = total_pages
        opportunities, total_count = get_opportunities_for_moderation(
            db, status_filter=status_filter or None, page=page, per_page=OPPS_PER_PAGE
        )

    return render_template(
        'admin/opportunities.html',
        active_page='admin',
        opportunities=opportunities,
        status_filter=status_filter,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )


@admin_bp.route('/opportunities/<int:opportunity_id>/status', methods=['POST'])
@admin_required
def moderate_opportunity(opportunity_id):
    db = get_db()
    new_status = request.form.get('status', '').strip()
    try:
        set_opportunity_moderation_status(db, opportunity_id, new_status)
    except ValueError:
        flash('Invalid moderation status.', 'error')
        return redirect(url_for('admin.opportunities_moderation'))
    except LookupError:
        flash('Opportunity not found.', 'error')
        return redirect(url_for('admin.opportunities_moderation'))

    log_admin_action(
        db, session['user_id'], action='MODERATE_OPPORTUNITY',
        target_type='opportunity', target_id=opportunity_id,
        details=f"Set moderation status to {new_status}"
    )
    flash(f'Opportunity marked as {new_status}.', 'success')
    return redirect(url_for('admin.opportunities_moderation'))


@admin_bp.route('/opportunities/<int:opportunity_id>/correct', methods=['POST'])
@admin_required
def correct_opportunity(opportunity_id):
    db = get_db()
    field = request.form.get('field', '').strip()
    value = request.form.get('value', '').strip()

    try:
        correct_opportunity_field(db, opportunity_id, field, value)
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('admin.opportunities_moderation'))
    except LookupError:
        flash('Opportunity not found.', 'error')
        return redirect(url_for('admin.opportunities_moderation'))

    log_admin_action(
        db, session['user_id'], action='CORRECT_OPPORTUNITY_DATA',
        target_type='opportunity', target_id=opportunity_id,
        details=f"Corrected '{field}' to: {value[:100]}"
    )

    # Reuse the existing scoring pipeline to bring every student's score
    # for this opportunity up to date with the correction, rather than
    # leaving them silently stale until the student happens to re-analyze.
    rescored_count = rescore_opportunity_for_all_students(db, opportunity_id)
    if rescored_count:
        flash(f'Opportunity data corrected. Scores recalculated for {rescored_count} student(s).', 'success')
    else:
        flash('Opportunity data corrected. No existing student scores needed recalculation.', 'success')
    return redirect(url_for('admin.opportunities_moderation'))


ACTIVITY_PER_PAGE = 25


@admin_bp.route('/activity')
@admin_required
def activity_log():
    db = get_db()
    try:
        admin_page = max(1, int(request.args.get('admin_page', 1)))
    except ValueError:
        admin_page = 1
    try:
        login_page = max(1, int(request.args.get('login_page', 1)))
    except ValueError:
        login_page = 1

    action_filter = request.args.get('action', '').strip()
    login_status = request.args.get('login_status', '').strip()  # 'success' | 'failed' | ''
    success_filter = {'success': True, 'failed': False}.get(login_status)

    admin_activity, admin_total = get_recent_admin_activity(
        db, limit=ACTIVITY_PER_PAGE, page=admin_page, action_filter=action_filter or None
    )
    login_activity, login_total = get_recent_login_activity(
        db, limit=ACTIVITY_PER_PAGE, page=login_page, success_filter=success_filter
    )

    return render_template(
        'admin/activity.html',
        active_page='admin',
        admin_activity=admin_activity,
        login_activity=login_activity,
        admin_page=admin_page,
        admin_total_pages=max(1, (admin_total + ACTIVITY_PER_PAGE - 1) // ACTIVITY_PER_PAGE),
        login_page=login_page,
        login_total_pages=max(1, (login_total + ACTIVITY_PER_PAGE - 1) // ACTIVITY_PER_PAGE),
        action_filter=action_filter,
        login_status=login_status
    )
