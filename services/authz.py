"""
Centralized authorization helpers for the Super Admin concept.

The Super Admin is identified by a specific email address (Config.SUPER_ADMIN_EMAIL)
AND a database role of 'admin' — never by session data alone. Keeping this
check in one place means the email string isn't scattered across routes/
models/templates, and any future change to how the Super Admin is identified
only has to happen here.
"""
from config import Config


def is_super_admin(user):
    """
    Returns True if the given user record (a dict with at least 'email'
    and 'role' keys) is the permanent Super Admin.

    Both the email AND the database role must match — a user record that
    matches the Super Admin email but has had its role changed (which
    shouldn't be possible via the app, but defense in depth) is not
    treated as the Super Admin for privilege purposes.
    """
    if not user:
        return False
    email = (user.get('email') or '').strip().lower()
    super_admin_email = (Config.SUPER_ADMIN_EMAIL or '').strip().lower()
    if not super_admin_email:
        return False
    return email == super_admin_email and user.get('role') == 'admin'


def is_super_admin_email(email):
    """
    Email-only check, for situations where no full user record is
    available yet (e.g. deciding whether to protect an account before it
    has been loaded). Prefer is_super_admin(user) whenever a user record
    is on hand.
    """
    if not email:
        return False
    return email.strip().lower() == (Config.SUPER_ADMIN_EMAIL or '').strip().lower()
