"""
OpportunityAI Configuration
----------------------------
Central configuration for the Flask application.
Uses environment variables where appropriate for security.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Absolute path to the project folder and .env file
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Explicitly load this project's .env file
load_dotenv(dotenv_path=ENV_FILE, override=True)

class Config:
    # ------------------------------------------------------------
    # Flask
    # ------------------------------------------------------------

    # Flask secret key for sessions — override with env var in production
    SECRET_KEY = os.environ.get(
        "OPPORTUNITYAI_SECRET_KEY",
        "dev-secret-key-change-in-production"
    )

    # ------------------------------------------------------------
    # PostgreSQL connection
    # ------------------------------------------------------------

    # Individual PostgreSQL variables are used only as a fallback when
    # DATABASE_URL is not provided.
    PGHOST = os.environ.get("PGHOST", "localhost")
    PGPORT = os.environ.get("PGPORT", "5432")
    PGDATABASE = os.environ.get("PGDATABASE", "opportunityai")
    PGUSER = os.environ.get("PGUSER", "postgres")
    PGPASSWORD = os.environ.get("PGPASSWORD", "postgres")

    # Supabase DATABASE_URL takes priority when present in .env
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
    )

    # ------------------------------------------------------------
    # Session settings
    # ------------------------------------------------------------

    # Flask's default signed, client-side session cookies are used.
    SESSION_PERMANENT = False

    # ------------------------------------------------------------
    # Future AI API integration
    # ------------------------------------------------------------

    AI_API_KEY = os.environ.get("OPPORTUNITYAI_API_KEY", None)
    AI_API_URL = os.environ.get("OPPORTUNITYAI_API_URL", None)

    # ------------------------------------------------------------
    # Google OAuth
    # ------------------------------------------------------------

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Auto-detect production URL from Vercel environment when
    # OAUTH_REDIRECT_BASE is not explicitly set.
    _vercel_url = os.environ.get("VERCEL_URL", "")
    _default_redirect = (
        f"https://{_vercel_url}" if _vercel_url
        else "http://127.0.0.1:5000"
    )
    OAUTH_REDIRECT_BASE = os.environ.get(
        "OAUTH_REDIRECT_BASE",
        _default_redirect
    )

    # ------------------------------------------------------------
    # Gmail token encryption
    # ------------------------------------------------------------

    TOKEN_ENCRYPTION_KEY = os.environ.get(
        "TOKEN_ENCRYPTION_KEY",
        "yQ2X3g8m9n0pB1cD4eF5gH6iJ7kL8mN9oP0qR1sT2uU="
    )

    # ------------------------------------------------------------
    # Gmail sync settings
    # ------------------------------------------------------------

    GMAIL_SYNC_MAX_RESULTS = 25
    GMAIL_OPPORTUNITY_THRESHOLD = 45

    # ------------------------------------------------------------
    # Opportunity scoring
    # ------------------------------------------------------------

    SCORING_WEIGHTS = {
        "eligibility": 0.25,
        "skills": 0.25,
        "education": 0.15,
        "interests": 0.15,
        "experience": 0.10,
        "location": 0.10,
    }

    # ------------------------------------------------------------
    # Urgency thresholds (days)
    # ------------------------------------------------------------

    URGENCY_CRITICAL_DAYS = 3
    URGENCY_HIGH_DAYS = 7
    URGENCY_MEDIUM_DAYS = 21

    # ------------------------------------------------------------
    # Trust score thresholds
    # ------------------------------------------------------------

    TRUST_HIGH = 75
    TRUST_MEDIUM = 50

    # ------------------------------------------------------------
    # Super Admin
    # ------------------------------------------------------------

    SUPER_ADMIN_EMAIL = os.environ.get(
        "SUPER_ADMIN_EMAIL",
        "dexantmg007@gmail.com"
    )

    # Used only when creating the Super Admin account for the first time.
    SUPER_ADMIN_PASSWORD = os.environ.get(
        "SUPER_ADMIN_PASSWORD",
        None
    )