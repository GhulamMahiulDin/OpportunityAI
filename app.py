import os
from datetime import datetime, date
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from config import Config
from database import db as db_module

# Import Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.profile import profile_bp
from routes.analyze import analyze_bp
from routes.opportunities import opportunities_bp
from routes.applications import applications_bp
from routes.settings import settings_bp
from routes.oauth import oauth_bp, init_oauth
from routes.inbox import inbox_bp
from routes.admin import admin_bp

def format_date(value, fmt='%b %d, %Y'):
    """
    Jinja filter: safely formats a date/datetime object OR a date-like
    string (e.g. from SQLite) into a friendly display string.
    """
    if not value:
        return ''
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    # Fallback: value is a string like '2026-01-15 10:30:00' or '2026-01-15'
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.split('.')[0])
        return parsed.strftime(fmt)
    except ValueError:
        return text[:10]

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.jinja_env.filters['dateformat'] = format_date

    # Initialize Database teardown
    db_module.init_app(app)

    # CSRF protection for every state-changing (POST/PUT/PATCH/DELETE) request.
    # Forms need a hidden csrf_token field; AJAX requests need an
    # X-CSRFToken header (see the csrf-token <meta> tag in base.html
    # and getCsrfToken() in app.js).
    CSRFProtect(app)

    # Initialize Google OAuth client (Sign in with Google + Gmail connect)
    init_oauth(app)

    # Loud, impossible-to-miss warnings if running on dev-only secrets.
    # These are fine for local testing but must never be used in production.
    if app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
        print("\n" + "!" * 70)
        print("! WARNING: Using the default dev SECRET_KEY.")
        print("! Set OPPORTUNITYAI_SECRET_KEY before deploying this anywhere real.")
        print("!" * 70 + "\n")

    if app.config['TOKEN_ENCRYPTION_KEY'] == 'yQ2X3g8m9n0pB1cD4eF5gH6iJ7kL8mN9oP0qR1sT2uU=':
        print("!" * 70)
        print("! WARNING: Using the default dev TOKEN_ENCRYPTION_KEY.")
        print("! This key protects stored Gmail tokens. Generate your own with:")
        print("!   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        print("! and set it as TOKEN_ENCRYPTION_KEY before deploying anywhere real.")
        print("!" * 70 + "\n")

    # Safety net: make sure the permanent Super Admin account exists even
    # if init_db.py was never explicitly re-run after this feature was
    # added. This is a no-op once the account exists. Guarded against a
    # completely fresh/un-migrated database (no 'users' table yet), in
    # which case init_db.py still needs to be run first as usual.
    #
    # Any failure here (bad DATABASE_URL, unreachable DB, missing schema)
    # is deliberately non-fatal — we don't want the whole app to refuse
    # to start over this — but it is LOUDLY logged, not silently
    # swallowed, so a broken production database connection shows up
    # immediately in your logs instead of surfacing later as a confusing
    # "login doesn't work" report.
    with app.app_context():
        try:
            from database.db import get_db
            from models.user import ensure_super_admin
            ensure_super_admin(get_db())
        except Exception as e:
            app.logger.error(
                "Startup check failed: could not verify/create the Super Admin "
                f"account. This usually means the database is unreachable or "
                f"hasn't been initialized yet (run init_db.py). Error: {e}"
            )

    @app.context_processor
    def inject_inbox_status():
        """Makes the inbox pending-count badge available in the sidebar on every page."""
        from flask import session
        if 'user_id' not in session:
            return {}
        try:
            from database.db import get_db
            from models.gmail import count_pending_synced_opportunities
            db = get_db()
            return {'sidebar_inbox_pending': count_pending_synced_opportunities(db, session['user_id'])}
        except Exception as e:
            app.logger.warning(f"Could not load inbox pending count: {e}")
            return {'sidebar_inbox_pending': 0}

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(analyze_bp)
    app.register_blueprint(opportunities_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(oauth_bp)
    app.register_blueprint(inbox_bp)
    app.register_blueprint(admin_bp)

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('base.html', title="403 — Access Denied"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('base.html', title="404 — Page Not Found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('base.html', title="500 — Internal Error"), 500

    return app

app = create_app()

if __name__ == '__main__':
    print("Starting OpportunityAI Application on http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000)
