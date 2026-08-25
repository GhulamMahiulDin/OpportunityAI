from flask import Blueprint, redirect, url_for, session, flash, current_app, request
from authlib.integrations.flask_client import OAuth
from database.db import get_db
from models.user import (
    get_user_by_google_id, get_user_by_email, create_user_from_google, link_google_account
)
from models.gmail import connect_gmail_account
from models.admin import log_login_attempt, record_login
from routes.dashboard import login_required
from routes.auth import _home_for_role

oauth_bp = Blueprint('oauth', __name__)

oauth = OAuth()


def init_oauth(app):
    """Called once from app.py's create_app() to register the Google client."""
    oauth.init_app(app)
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )


def _google_creds_missing():
    return not current_app.config.get('GOOGLE_CLIENT_ID') or not current_app.config.get('GOOGLE_CLIENT_SECRET')


# ============================================================
# Sign in with Google (account login/registration)
# ============================================================

def _redirect_uri(endpoint):
    """
    Builds the OAuth redirect URI.
    If we are running on a remote host (non-localhost), we dynamically use the
    incoming request's host to ensure the redirect URI matches the exact domain
    the user is currently visiting (e.g. https://opportunity-ai-kappa.vercel.app).
    Otherwise, we use the configured OAUTH_REDIRECT_BASE (for local development).
    """
    req_host = request.host
    is_local = not req_host or '127.0.0.1' in req_host or 'localhost' in req_host

    if not is_local:
        scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
        base = f'{scheme}://{req_host}'
    else:
        base = current_app.config['OAUTH_REDIRECT_BASE'].rstrip('/')

    path = url_for(endpoint)
    return f'{base}{path}'


@oauth_bp.route('/auth/google/login')
def google_login():
    if _google_creds_missing():
        flash('Google Sign-In is not configured yet. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.', 'error')
        return redirect(url_for('auth.login'))
    redirect_uri = _redirect_uri('oauth.google_login_callback')
    return oauth.google.authorize_redirect(redirect_uri)


@oauth_bp.route('/auth/google/callback')
def google_login_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash('Google Sign-In was cancelled or failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    userinfo = token.get('userinfo') or {}
    google_id = userinfo.get('sub')
    email = userinfo.get('email')
    name = userinfo.get('name') or (email.split('@')[0] if email else 'Student')
    picture = userinfo.get('picture', '')

    if not google_id or not email:
        flash('Could not read your Google profile. Please try again.', 'error')
        return redirect(url_for('auth.login'))

    db = get_db()
    user = get_user_by_google_id(db, google_id)

    if not user:
        # Maybe they already have a password account with this email — link it.
        existing = get_user_by_email(db, email)
        if existing:
            if not existing.get('is_active', 1):
                flash('This account has been deactivated. Contact an administrator.', 'error')
                return redirect(url_for('auth.login'))
            link_google_account(db, existing['id'], google_id, picture)
            user = existing
        else:
            user_id = create_user_from_google(db, name, email, google_id, picture)
            user = {'id': user_id, 'name': name, 'email': email, 'role': 'student'}
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['role'] = 'student'
            record_login(db, user['id'])
            log_login_attempt(db, email, success=True, user_id=user['id'], ip_address=request.remote_addr or '')
            flash(f'Welcome, {name}! Your account is ready — let\'s finish your profile.', 'success')
            return redirect(url_for('profile.profile_page'))

    if not user.get('is_active', 1):
        flash('This account has been deactivated. Contact an administrator.', 'error')
        return redirect(url_for('auth.login'))

    session.clear()
    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']
    session['role'] = user.get('role', 'student')
    record_login(db, user['id'])
    log_login_attempt(db, email, success=True, user_id=user['id'], ip_address=request.remote_addr or '')
    flash(f"Welcome back, {user['name']}!", 'success')
    return _home_for_role(user.get('role'))


# ============================================================
# Connect Gmail (read-only, for the inbox sync feature)
# ============================================================

@oauth_bp.route('/gmail/connect')
@login_required
def gmail_connect():
    if _google_creds_missing():
        flash('Google Sign-In is not configured yet. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.', 'error')
        return redirect(url_for('settings.settings_page'))
    redirect_uri = _redirect_uri('oauth.gmail_callback')
    gmail_scope = 'openid email profile https://www.googleapis.com/auth/gmail.readonly'
    return oauth.google.authorize_redirect(
        redirect_uri,
        scope=gmail_scope,
        access_type='offline',
        prompt='consent',
    )


@oauth_bp.route('/gmail/callback')
@login_required
def gmail_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash('Connecting Gmail failed or was cancelled. Please try again.', 'error')
        return redirect(url_for('settings.settings_page'))

    userinfo = token.get('userinfo') or {}
    gmail_address = userinfo.get('email', session.get('user_email', ''))
    refresh_token = token.get('refresh_token')

    if not refresh_token:
        flash(
            'Google did not return a refresh token. If you\'ve connected before, '
            'revoke access at myaccount.google.com/permissions and try again.',
            'error'
        )
        return redirect(url_for('settings.settings_page'))

    token_dict = {
        'access_token': token.get('access_token'),
        'refresh_token': refresh_token,
        'expires_at': token.get('expires_at', 0),
    }

    db = get_db()
    connect_gmail_account(db, session['user_id'], gmail_address, token_dict)
    flash(f'Gmail connected ({gmail_address}). You can sync your inbox now.', 'success')
    return redirect(url_for('inbox.inbox_page'))
