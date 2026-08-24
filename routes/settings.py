from flask import Blueprint, render_template, session, redirect, url_for, flash
from database.db import get_db
from models.user import get_user_by_id
from models.gmail import get_gmail_account, disconnect_gmail_account
from routes.dashboard import login_required

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def settings_page():
    user_id = session['user_id']
    db = get_db()
    user = get_user_by_id(db, user_id)
    gmail_account = get_gmail_account(db, user_id)
    
    return render_template(
        'settings.html',
        active_page='settings',
        user=user,
        gmail_account=gmail_account
    )

@settings_bp.route('/settings/gmail/disconnect', methods=['POST'])
@login_required
def gmail_disconnect():
    user_id = session['user_id']
    db = get_db()
    disconnect_gmail_account(db, user_id)
    flash('Gmail disconnected. Your synced opportunities are kept, but syncing has stopped.', 'info')
    return redirect(url_for('settings.settings_page'))
