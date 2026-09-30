import json


# ============================================================
# ADMIN ACTIVITY LOG (audit trail)
# ============================================================

def log_admin_action(db, admin_id, action, target_type='', target_id=None, details=''):
    """
    Records an admin action for accountability. Called by every admin
    route that changes something (deactivating a user, moderating an
    opportunity, correcting data, etc).
    """
    db.execute(
        """INSERT INTO admin_activity_logs (admin_id, action, target_type, target_id, details)
           VALUES (?, ?, ?, ?, ?)""",
        (admin_id, action, target_type, target_id, details)
    )
    db.commit()


def get_recent_admin_activity(db, limit=25, page=1, action_filter=None, admin_filter=None):
    """
    Retrieves a page of admin activity log entries, most recent first.
    Returns (entries, total_count). `limit` doubles as per_page here.
    """
    where_clause = "WHERE 1=1"
    params = []
    if action_filter:
        where_clause += " AND l.action = ?"
        params.append(action_filter)
    if admin_filter:
        where_clause += " AND l.admin_id = ?"
        params.append(admin_filter)

    total_count = db.execute(
        f"SELECT COUNT(*) FROM admin_activity_logs l {where_clause}", params
    ).fetchone()[0]

    page = max(1, page)
    offset = (page - 1) * limit
    rows = db.execute(
        f"""SELECT l.*, u.name as admin_name, u.email as admin_email
           FROM admin_activity_logs l
           JOIN users u ON u.id = l.admin_id
           {where_clause}
           ORDER BY l.created_at DESC LIMIT ? OFFSET ?""",
        params + [limit, offset]
    ).fetchall()
    return [dict(r) for r in rows], total_count


# ============================================================
# LOGIN LOG (security visibility — login/logout/failed attempts only,
# never behavioral tracking of what a student does inside the app)
# ============================================================

def log_login_attempt(db, email_attempted, success, user_id=None, ip_address=''):
    db.execute(
        """INSERT INTO login_logs (user_id, email_attempted, success, ip_address)
           VALUES (?, ?, ?, ?)""",
        (user_id, email_attempted, int(success), ip_address)
    )
    db.commit()


def get_recent_login_activity(db, limit=25, page=1, success_filter=None):
    """
    Retrieves a page of login log entries, most recent first.
    Returns (entries, total_count). success_filter: True/False/None (any).
    """
    where_clause = "WHERE 1=1"
    params = []
    if success_filter is not None:
        where_clause += " AND success = ?"
        params.append(int(success_filter))

    total_count = db.execute(
        f"SELECT COUNT(*) FROM login_logs {where_clause}", params
    ).fetchone()[0]

    page = max(1, page)
    offset = (page - 1) * limit
    rows = db.execute(
        f"SELECT * FROM login_logs {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    return [dict(r) for r in rows], total_count


# ============================================================
# USER MANAGEMENT
# ============================================================

def get_all_users(db, search=None, role_filter=None, page=1, per_page=25):
    """
    Retrieves a page of users matching the given filters.
    Returns (users, total_count) so callers can render pagination controls
    without loading every user into memory.
    """
    where_clause = "WHERE 1=1"
    params = []
    if search:
        where_clause += " AND (name LIKE ? OR email LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])
    if role_filter:
        where_clause += " AND role = ?"
        params.append(role_filter)

    total_count = db.execute(f"SELECT COUNT(*) FROM users {where_clause}", params).fetchone()[0]

    page = max(1, page)
    offset = (page - 1) * per_page
    query = f"""
        SELECT id, name, email, role, is_active, last_login, created_at,
               google_id IS NOT NULL as is_google_account
        FROM users
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    rows = db.execute(query, params + [per_page, offset]).fetchall()
    return [dict(r) for r in rows], total_count


def get_user_admin_detail(db, user_id):
    """User info plus their profile/activity summary, for the admin detail view."""
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return None
    user = dict(user)

    profile = db.execute("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,)).fetchone()
    user['profile'] = dict(profile) if profile else None

    if profile:
        student_id = profile['id']
        user['opportunity_count'] = db.execute(
            "SELECT COUNT(*) FROM opportunities WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        user['application_count'] = db.execute(
            "SELECT COUNT(*) FROM applications WHERE student_id = ?", (student_id,)
        ).fetchone()[0]
    else:
        user['opportunity_count'] = 0
        user['application_count'] = 0

    return user


def set_user_active_status(db, user_id, is_active):
    """
    Activates/deactivates a user. The Super Admin account can never be
    deactivated through this function, regardless of who calls it or how
    the request was constructed — this is enforced here (not just in the
    route/UI) so it can't be bypassed with a hand-crafted request.
    """
    from services.authz import is_super_admin
    target = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        raise LookupError("user not found")
    if is_super_admin(dict(target)) and not is_active:
        raise PermissionError("The Super Admin account cannot be deactivated.")
    db.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(is_active), user_id))
    db.commit()


def set_user_role(db, user_id, role):
    """
    Changes a user's role. The Super Admin account's role can never be
    changed away from 'admin' through this function — enforced here so
    the protection holds even if a route-level check is ever missed or
    bypassed via a direct request.
    """
    if role not in ('student', 'admin'):
        raise ValueError("role must be 'student' or 'admin'")
    from services.authz import is_super_admin
    target = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        raise LookupError("user not found")
    if is_super_admin(dict(target)) and role != 'admin':
        raise PermissionError("The Super Admin's role cannot be changed.")
    db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    db.commit()


def record_login(db, user_id):
    db.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    db.commit()


# ============================================================
# OPPORTUNITY MODERATION
# ============================================================

def get_opportunities_for_moderation(db, status_filter=None, page=1, per_page=20):
    """
    Retrieves a page of opportunities for the moderation queue.
    Returns (opportunities, total_count).
    """
    where_clause = "WHERE 1=1"
    params = []
    if status_filter:
        where_clause += " AND o.moderation_status = ?"
        params.append(status_filter)

    total_count = db.execute(
        f"SELECT COUNT(*) FROM opportunities o {where_clause}", params
    ).fetchone()[0]

    page = max(1, page)
    offset = (page - 1) * per_page
    query = f"""
        SELECT o.*, u.name as submitted_by_name, u.email as submitted_by_email,
               (SELECT AVG(trust_score) FROM opportunity_scores WHERE opportunity_id = o.id) as avg_trust_score
        FROM opportunities o
        JOIN users u ON u.id = o.user_id
        {where_clause}
        ORDER BY o.created_at DESC
        LIMIT ? OFFSET ?
    """
    rows = db.execute(query, params + [per_page, offset]).fetchall()
    return [dict(r) for r in rows], total_count


def set_opportunity_moderation_status(db, opportunity_id, status):
    if status not in ('pending', 'approved', 'flagged', 'removed'):
        raise ValueError("invalid moderation status")
    existing = db.execute("SELECT id FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
    if not existing:
        raise LookupError("opportunity not found")
    db.execute("UPDATE opportunities SET moderation_status = ? WHERE id = ?", (status, opportunity_id))
    db.commit()


def correct_opportunity_field(db, opportunity_id, field, value):
    """
    Lets an admin correct extracted data (e.g. a wrong deadline) rather
    than manually overriding the AI-computed scores. Only a safe allow-list
    of fields can be edited this way.
    """
    allowed_fields = {
        'title', 'organization', 'type', 'description', 'location',
        'remote_onsite', 'deadline', 'application_url', 'eligibility_summary',
        'documents_needed', 'selection_process'
    }
    if field not in allowed_fields:
        raise ValueError(f"'{field}' is not an editable field")
    existing = db.execute("SELECT id FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
    if not existing:
        raise LookupError("opportunity not found")
    db.execute(f"UPDATE opportunities SET {field} = ? WHERE id = ?", (value, opportunity_id))
    db.commit()


# ============================================================
# SYSTEM ANALYTICS (admin dashboard)
# ============================================================

def get_system_stats(db):
    """
    System-wide analytics for the admin dashboard. Every value is safe
    against an empty database (0s, not None/NaN), and every score-based
    stat (high/low match, urgent, averages, type distribution) excludes
    'removed' opportunities so a moderator removing something also removes
    it from the numbers, not just from student-facing listings.
    """
    def count(sql, params=()):
        row = db.execute(sql, params).fetchone()
        return row[0] if row and row[0] is not None else 0

    total_users = count("SELECT COUNT(*) FROM users")
    active_today = count(
        "SELECT COUNT(*) FROM users WHERE date(last_login) = CURRENT_DATE"
    )
    total_opportunities = count("SELECT COUNT(*) FROM opportunities WHERE moderation_status != 'removed'")
    total_applications = count("SELECT COUNT(*) FROM applications")
    gmail_connected = count("SELECT COUNT(*) FROM gmail_accounts")

    # One combined query for the score-derived counts + averages, joined
    # against opportunities so 'removed' items are excluded consistently,
    # instead of four-plus separate round trips.
    agg_row = db.execute(
        """
        SELECT
            COUNT(*) AS total_analyses,
            SUM(CASE WHEN os.match_score >= 75 THEN 1 ELSE 0 END) AS high_match,
            SUM(CASE WHEN os.match_score < 50 THEN 1 ELSE 0 END) AS low_match,
            SUM(CASE WHEN os.urgency_score >= 75 THEN 1 ELSE 0 END) AS urgent,
            AVG(os.match_score) AS avg_match,
            AVG(os.trust_score) AS avg_trust,
            AVG(os.completeness_score) AS avg_completeness
        FROM opportunity_scores os
        JOIN opportunities o ON o.id = os.opportunity_id
        WHERE o.moderation_status != 'removed'
        """
    ).fetchone()

    total_analyses = agg_row['total_analyses'] or 0
    high_match = agg_row['high_match'] or 0
    low_match = agg_row['low_match'] or 0
    urgent = agg_row['urgent'] or 0
    avg_match = round(agg_row['avg_match'], 1) if agg_row['avg_match'] is not None else 0
    avg_trust = round(agg_row['avg_trust'], 1) if agg_row['avg_trust'] is not None else 0
    avg_completeness = round(agg_row['avg_completeness'], 1) if agg_row['avg_completeness'] is not None else 0

    flagged = count("SELECT COUNT(*) FROM opportunities WHERE moderation_status = 'flagged'")
    pending = count("SELECT COUNT(*) FROM opportunities WHERE moderation_status = 'pending'")
    removed = count("SELECT COUNT(*) FROM opportunities WHERE moderation_status = 'removed'")

    type_rows = db.execute(
        "SELECT type, COUNT(*) as c FROM opportunities WHERE moderation_status != 'removed' GROUP BY type ORDER BY c DESC"
    ).fetchall()
    opportunity_types = [dict(r) for r in type_rows]

    return {
        'total_users': total_users,
        'active_today': active_today,
        'total_opportunities': total_opportunities,
        'total_applications': total_applications,
        'total_analyses': total_analyses,
        'high_match': high_match,
        'low_match': low_match,
        'urgent': urgent,
        'flagged': flagged,
        'pending': pending,
        'removed': removed,
        'avg_match': avg_match,
        'avg_trust': avg_trust,
        'avg_completeness': avg_completeness,
        'opportunity_types': opportunity_types,
        'gmail_connected': gmail_connected,
    }
