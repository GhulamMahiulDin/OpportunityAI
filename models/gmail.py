import json
from services.crypto_util import encrypt_text, decrypt_text


def connect_gmail_account(db, user_id, gmail_address, token_dict):
    """
    Stores (or replaces) the Gmail connection for a user. The token dict
    (access_token, refresh_token, expires_at) is encrypted before storage.
    """
    encrypted = encrypt_text(json.dumps(token_dict))
    db.execute(
        """INSERT INTO gmail_accounts (user_id, gmail_address, encrypted_token, connected_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id) DO UPDATE SET
               gmail_address = excluded.gmail_address,
               encrypted_token = excluded.encrypted_token,
               connected_at = CURRENT_TIMESTAMP""",
        (user_id, gmail_address, encrypted)
    )
    db.commit()


def get_gmail_account(db, user_id):
    """
    Returns {'gmail_address', 'token': {...decrypted dict...}, 'last_synced_at', 'connected_at'}
    or None if the user hasn't connected Gmail.
    """
    row = db.execute("SELECT * FROM gmail_accounts WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        data['token'] = json.loads(decrypt_text(data['encrypted_token']))
    except Exception:
        data['token'] = None
    return data


def update_gmail_token(db, user_id, token_dict):
    """Updates just the stored token (e.g. after an access-token refresh)."""
    encrypted = encrypt_text(json.dumps(token_dict))
    db.execute("UPDATE gmail_accounts SET encrypted_token = ? WHERE user_id = ?", (encrypted, user_id))
    db.commit()


def mark_synced_now(db, user_id):
    db.execute("UPDATE gmail_accounts SET last_synced_at = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
    db.commit()


def disconnect_gmail_account(db, user_id):
    db.execute("DELETE FROM gmail_accounts WHERE user_id = ?", (user_id,))
    db.commit()


def has_seen_message(db, user_id, gmail_message_id):
    row = db.execute(
        "SELECT id FROM synced_emails WHERE user_id = ? AND gmail_message_id = ?",
        (user_id, gmail_message_id)
    ).fetchone()
    return row is not None


def record_synced_email(db, user_id, gmail_message_id, subject, sender, received_at,
                         classifier_score, is_opportunity, opportunity_id=None):
    db.execute(
        """INSERT OR IGNORE INTO synced_emails
           (user_id, gmail_message_id, subject, sender, received_at,
            classifier_score, is_opportunity, status, opportunity_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, gmail_message_id, subject, sender, received_at,
         classifier_score, int(is_opportunity),
         'pending' if is_opportunity else 'dismissed', opportunity_id)
    )
    db.commit()


def get_pending_synced_opportunities(db, user_id, student_id=0):
    """
    Returns synced emails that turned into real opportunities and are
    still awaiting the student's review (i.e. not dismissed and not
    already tracked as an application), newest first, joined with their
    computed scores so the inbox page can show match/urgency/trust at a glance.
    """
    rows = db.execute(
        """SELECT se.*, o.title, o.organization, o.type, o.deadline, o.location,
                  os.match_score, os.urgency_score, os.trust_score, os.completeness_score,
                  os.recommendation, os.recommendation_icon
           FROM synced_emails se
           JOIN opportunities o ON o.id = se.opportunity_id
           LEFT JOIN opportunity_scores os ON os.opportunity_id = o.id
           LEFT JOIN applications a ON a.opportunity_id = o.id AND a.student_id = ?
           WHERE se.user_id = ? AND se.status = 'pending' AND se.opportunity_id IS NOT NULL
                 AND a.id IS NULL
           ORDER BY os.match_score DESC, se.created_at DESC""",
        (student_id, user_id)
    ).fetchall()
    return [dict(r) for r in rows]


def count_pending_synced_opportunities(db, user_id):
    row = db.execute(
        "SELECT COUNT(*) as c FROM synced_emails WHERE user_id = ? AND status = 'pending' AND opportunity_id IS NOT NULL",
        (user_id,)
    ).fetchone()
    return row[0] if row else 0


def mark_synced_email_status(db, user_id, synced_email_id, status):
    db.execute(
        "UPDATE synced_emails SET status = ? WHERE id = ? AND user_id = ?",
        (status, synced_email_id, user_id)
    )
    db.commit()


def get_recent_sync_log(db, user_id, limit=15):
    """Recent synced emails (opportunity or not) — useful for a 'what did we check' view."""
    rows = db.execute(
        """SELECT * FROM synced_emails WHERE user_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        (user_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]
