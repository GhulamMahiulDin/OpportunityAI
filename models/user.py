import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

def create_user(db, name, email, password):
    """
    Creates a new user with a hashed password, and initializes a blank student profile.
    Returns the user id.
    """
    db.row_factory = sqlite3.Row
    hashed = generate_password_hash(password)
    
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, hashed)
    )
    user_id = cursor.lastrowid
    
    # Create blank profile
    db.execute(
        "INSERT INTO student_profiles (user_id) VALUES (?)",
        (user_id,)
    )
    
    db.commit()
    return user_id

def create_user_from_google(db, name, email, google_id, picture_url=''):
    """
    Creates a new user from a Google Sign-In profile. These accounts have
    no password_hash — they can only log in via Google (unless the user
    later sets one, which isn't wired up yet but the column supports it).
    """
    db.row_factory = sqlite3.Row
    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash, google_id, picture_url) VALUES (?, ?, NULL, ?, ?)",
        (name, email, google_id, picture_url)
    )
    user_id = cursor.lastrowid
    db.execute("INSERT INTO student_profiles (user_id) VALUES (?)", (user_id,))
    db.commit()
    return user_id

def get_user_by_google_id(db, google_id):
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
    return dict(row) if row else None

def link_google_account(db, user_id, google_id, picture_url=''):
    """Links a Google identity to an existing (email/password) account."""
    db.execute(
        "UPDATE users SET google_id = ?, picture_url = COALESCE(NULLIF(?, ''), picture_url) WHERE id = ?",
        (google_id, picture_url, user_id)
    )
    db.commit()

def get_user_by_email(db, email):
    """
    Retrieves a user by email.
    """
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        return dict(row)
    return None

def get_user_by_id(db, user_id):
    """
    Retrieves a user by id.
    """
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row:
        return dict(row)
    return None

def verify_password(stored_hash, password):
    """
    Verifies a password against the stored hash. Returns False (instead of
    raising) for Google-only accounts that have no password set.
    """
    if not stored_hash:
        return False
    return check_password_hash(stored_hash, password)


def ensure_super_admin(db):
    """
    Ensures the permanent Super Admin account (Config.SUPER_ADMIN_EMAIL)
    exists with role='admin', without ever duplicating the account or
    touching an existing password.

    - If the account already exists: only its role is corrected to
      'admin' if it had drifted; everything else (password hash,
      profile, history) is left untouched.
    - If the account does not exist: it's created using
      Config.SUPER_ADMIN_PASSWORD if that env var is set. If it isn't
      set, a loudly-flagged dev-only fallback password is used so local
      development still works — this is NOT silent, unlike leaving the
      account uncreated would be, and it must never be relied on in
      production.

    Safe to call on every app startup and from init_db.py; it is a no-op
    once the account exists and already has the right role.
    """
    from config import Config
    import sqlite3 as _sqlite3

    email = (Config.SUPER_ADMIN_EMAIL or '').strip()
    if not email:
        return None

    db.row_factory = _sqlite3.Row
    existing = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if existing:
        existing = dict(existing)
        if existing.get('role') != 'admin':
            db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (existing['id'],))
            db.commit()
        return existing['id']

    password = Config.SUPER_ADMIN_PASSWORD
    using_dev_fallback = not password
    if using_dev_fallback:
        password = 'ChangeMe123!'
        print("\n" + "!" * 70)
        print("! WARNING: Creating the Super Admin account with a DEV-ONLY")
        print(f"! DEFAULT PASSWORD because SUPER_ADMIN_PASSWORD is not set.")
        print(f"!   Email:    {email}")
        print(f"!   Password: {password}")
        print("! Set the SUPER_ADMIN_PASSWORD environment variable and restart")
        print("! before using this anywhere other than local development.")
        print("!" * 70 + "\n")

    user_id = create_user(db, "Super Admin", email, password)
    db.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
    db.commit()
    return user_id
