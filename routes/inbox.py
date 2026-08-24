from flask import Blueprint, render_template, redirect, url_for, session, flash, current_app
from database.db import get_db
from models.profile import get_profile
from models.gmail import (
    get_gmail_account, update_gmail_token, mark_synced_now, has_seen_message,
    record_synced_email, get_pending_synced_opportunities, mark_synced_email_status,
    get_recent_sync_log
)
from services.gmail_service import (
    get_valid_access_token, list_recent_messages, get_message, parse_message,
    build_sync_query, GmailAuthError
)
from services.classifier import classify_email
from services.analyzer import analyze_opportunity
from services.pipeline import run_full_analysis
from routes.dashboard import login_required

inbox_bp = Blueprint('inbox', __name__)


@inbox_bp.route('/inbox')
@login_required
def inbox_page():
    user_id = session['user_id']
    db = get_db()
    profile = get_profile(db, user_id)
    student_id = profile['id'] if profile else 0

    gmail_account = get_gmail_account(db, user_id)
    pending = get_pending_synced_opportunities(db, user_id, student_id)
    recent_log = get_recent_sync_log(db, user_id, limit=10)

    return render_template(
        'inbox.html',
        active_page='inbox',
        gmail_account=gmail_account,
        pending=pending,
        recent_log=recent_log
    )


@inbox_bp.route('/gmail/sync', methods=['POST'])
@login_required
def gmail_sync():
    user_id = session['user_id']
    db = get_db()

    gmail_account = get_gmail_account(db, user_id)
    if not gmail_account or not gmail_account.get('token'):
        flash('Connect your Gmail account first.', 'error')
        return redirect(url_for('settings.settings_page'))

    profile = get_profile(db, user_id)
    student_id = profile['id'] if profile else 0

    try:
        access_token, updated_token = get_valid_access_token(gmail_account['token'])
        if updated_token:
            update_gmail_token(db, user_id, updated_token)

        sync_query = build_sync_query(gmail_account.get('last_synced_at'))
        messages = list_recent_messages(
            access_token, query=sync_query,
            max_results=current_app.config.get('GMAIL_SYNC_MAX_RESULTS', 25)
        )

        checked = 0
        found = 0
        threshold = current_app.config.get('GMAIL_OPPORTUNITY_THRESHOLD', 45)

        for m in messages:
            msg_id = m['id']
            if has_seen_message(db, user_id, msg_id):
                continue

            full_msg = get_message(access_token, msg_id)
            parsed = parse_message(full_msg)
            checked += 1

            classification = classify_email(parsed['subject'], parsed['body_text'], parsed['sender'])
            is_opportunity = classification['is_opportunity'] and classification['score'] >= threshold

            opp_id = None
            if is_opportunity:
                source_text = f"Subject: {parsed['subject']}\n\n{parsed['body_text']}"
                extracted = analyze_opportunity(source_text)
                if not extracted.get('title'):
                    extracted['title'] = parsed['subject'] or 'Untitled opportunity'
                extracted['source_text'] = parsed['body_text'][:3000]

                opp_id, _ = run_full_analysis(
                    db, user_id, profile, student_id, extracted, source='gmail'
                )
                found += 1

            record_synced_email(
                db, user_id, msg_id, parsed['subject'], parsed['sender'],
                parsed['received_at'], classification['score'], is_opportunity,
                opportunity_id=opp_id
            )

        mark_synced_now(db, user_id)

        if found > 0:
            flash(f'Sync complete — checked {checked} new email(s), found {found} opportunity match(es)!', 'success')
        else:
            flash(f'Sync complete — checked {checked} new email(s), nothing new matched your interests.', 'info')

    except GmailAuthError as e:
        flash(str(e), 'error')
        return redirect(url_for('settings.settings_page'))
    except Exception as e:
        flash(f'Sync failed: {str(e)[:150]}', 'error')

    return redirect(url_for('inbox.inbox_page'))


@inbox_bp.route('/inbox/<int:synced_email_id>/dismiss', methods=['POST'])
@login_required
def dismiss(synced_email_id):
    user_id = session['user_id']
    db = get_db()
    mark_synced_email_status(db, user_id, synced_email_id, 'dismissed')
    flash('Dismissed.', 'info')
    return redirect(url_for('inbox.inbox_page'))
