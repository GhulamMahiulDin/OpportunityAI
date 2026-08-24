from functools import wraps
from flask import session, redirect, url_for, abort


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        from database.db import get_db
        from models.profile import ensure_profile_exists
        from models.user import get_user_by_id

        db = get_db()

        # Safety net: guarantees every logged-in user has a student_profiles
        # row before any page/route logic runs, so scoring code never has
        # to deal with profile being None (e.g. Google accounts linked to
        # older records, or any historical gap in profile creation).
        ensure_profile_exists(db, session['user_id'])

        # If an admin deactivates this account mid-session, stop honoring
        # the session immediately instead of waiting for it to expire.
        user = get_user_by_id(db, session['user_id'])
        if not user or not user.get('is_active', 1):
            session.clear()
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Protects a route so only users with role == 'admin' can access it.
    Non-admins (including logged-out visitors) get a real 403, not just
    a hidden button — this is enforced at the route level, not the UI.

    Crucially, this re-checks the DATABASE on every request rather than
    trusting session['role']. session['role'] is only a snapshot taken at
    login time — if an admin's role is revoked (or their account is
    deactivated) while they still hold an active session/cookie, the old
    session data would otherwise keep letting them into /admin/*.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        from database.db import get_db
        from models.user import get_user_by_id

        db = get_db()
        user = get_user_by_id(db, session['user_id'])

        # 1. User must still exist, 2. must still be active,
        # 3. must currently hold the admin role in the database (not just
        # in the session). Any failure revokes access immediately.
        if not user or not user.get('is_active', 1) or user.get('role') != 'admin':
            if not user or not user.get('is_active', 1):
                session.clear()
                return redirect(url_for('auth.login'))
            abort(403)

        # Keep the session's cached copy honest for the rest of the app
        # (e.g. sidebar UI) now that we've confirmed it from the database.
        session['role'] = user['role']

        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """
    Protects a route so only the permanent Super Admin account can
    access it — used for privilege-management actions (granting or
    removing another user's admin role) that must stay centralized to a
    single account rather than being usable by any admin.

    Re-checks the database on every request, same reasoning as
    admin_required: session data is only a snapshot and must never be
    the sole source of truth for a security decision.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        from database.db import get_db
        from models.user import get_user_by_id
        from services.authz import is_super_admin

        db = get_db()
        user = get_user_by_id(db, session['user_id'])

        if not user or not user.get('is_active', 1):
            session.clear()
            return redirect(url_for('auth.login'))

        if not is_super_admin(user):
            abort(403)

        session['role'] = user['role']

        return f(*args, **kwargs)
    return decorated_function
