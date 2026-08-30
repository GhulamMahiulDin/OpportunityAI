# OpportunityAI

#### Video Demo: https://youtu.be/r6hkWPlkVc4

#### Description:

OpportunityAI is an AI-powered web application designed to help students discover important opportunities that might otherwise be overlooked in their emails.

# OpportunityAI — AI-Powered Opportunity Intelligence for Students

> **"Find what matters. Know your match. Apply with confidence."**

OpportunityAI is a complete, modern, responsive Flask web application designed for students to analyze academic and career opportunities (internships, scholarships, competitions, fellowships, research roles, hackathons, and jobs).

Instead of just summarizing emails, **OpportunityAI helps students evaluate whether an opportunity deserves their time and guides them step-by-step through the application process** — and can now read a student's Gmail directly to surface opportunities they'd otherwise scroll past.

---

## 🛠️ Technology Stack

Built strictly using fundamental technologies:

- **Frontend**: HTML5, CSS3 (Vanilla Dark UI Design System), Vanilla JavaScript (ES6, AJAX via `fetch`)
- **Backend**: Python, Flask (Blueprints architecture)
- **Database**: PostgreSQL (Raw SQL with parameterized queries, NO ORM)
- **Algorithms**: Python rule-based NLP extraction and transparent multi-dimensional scoring
- **Auth & Inbox**: Google OAuth2 (Authlib) for Sign-In and read-only Gmail sync

---

## 🚀 Quick Start Guide

### 1. Requirements

- Python 3.8+
- `pip`
- **PostgreSQL** (13+ recommended) installed and running — either locally or a hosted instance (Render, Railway, Supabase, Heroku Postgres, etc. all work)

### 2. Install Dependencies

```bash
cd OpportunityAI
pip install -r requirements.txt
```

This includes `psycopg2-binary`, the PostgreSQL driver.

### 3. Configure your database connection

OpportunityAI reads its PostgreSQL connection from environment variables. You have two options:

**Option A — individual variables** (defaults shown; override any you need to):
```bash
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=opportunityai
export PGUSER=postgres
export PGPASSWORD=postgres
```

**Option B — a single connection string** (what most hosting providers give you), which overrides Option A entirely if set:
```bash
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
```

**On a local PostgreSQL install you control**, you don't need to manually create the database first — `init_db.py` will create it automatically if it doesn't exist.

**On a hosted provider** (Supabase, Render Postgres, Railway, etc.), the database is already created for you when you provision it in their dashboard — `init_db.py` will detect it already exists and skip straight to creating the tables. Your hosted database user typically won't have permission to create *new* databases (and doesn't need to) — `init_db.py` handles that gracefully and just proceeds using the database your provider already gave you. Just copy their connection string into `DATABASE_URL` exactly as they give it to you.

### 4. Initialize the Database & Load Sample Data

Run `init_db.py` to create all tables and populate them with seed skills, interests, preferences, a demo student profile, and **11 realistic sample opportunities**:

```bash
python init_db.py
```

If tables already exist (e.g. you're re-running this), you'll be asked to confirm before anything is dropped and recreated. Pass `--force` to skip that prompt (useful in scripts/CI).

**Demo Account Credentials:**
- **Student** — Email: `demo@opportunityai.org` · Password: `password123`
- **Admin** — Email: `admin@opportunityai.org` · Password: `adminpass123`

### 5. Run the Application

```bash
python app.py
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 📐 Project Structure

```text
OpportunityAI/
│
├── app.py                      # Flask app factory and entry point
├── config.py                   # Central configuration & scoring weights
├── init_db.py                  # Database initialization & sample data generator
├── requirements.txt            # Python dependencies (Flask, Werkzeug)
│
├── database/
│   ├── db.py                   # PostgreSQL connection layer (sqlite3-compatible API wrapper)
│   └── schema.sql              # PostgreSQL database schema (13+ tables)
│
├── models/                     # Raw SQL Data Access Layer
│   ├── user.py                 # User CRUD & password hashing
│   ├── profile.py              # Profile, skills, interests & preferences CRUD
│   ├── opportunity.py          # Opportunity, requirement & score CRUD
│   └── application.py          # Application tracking & checklist generator
│
├── services/                   # Business Logic & Scoring Services
│   ├── analyzer.py             # Rule-based NLP opportunity text extractor
│   ├── scoring.py              # Transparent Personal Match Scoring Engine
│   ├── urgency.py              # Deadline & complexity urgency calculator
│   ├── trust.py                # Trust & authenticity signal analyzer
│   └── completeness.py         # 11-point information completeness checker
│
├── routes/                     # Modular Flask Blueprints
│   ├── auth.py                 # Register, Login, Logout
│   ├── dashboard.py            # Dashboard overview & high-priority matches
│   ├── profile.py              # Profile editing & tag management
│   ├── analyze.py              # Paste & manual entry opportunity analysis
│   ├── opportunities.py        # Opportunity list, search, filter & detail
│   ├── applications.py         # Application status tracker & interactive checklists
│   └── settings.py             # Account settings & future integrations
│
├── templates/                  # Jinja2 HTML5 Templates
│   ├── base.html               # Responsive dark shell layout with mobile drawer
│   ├── login.html              # Login form
│   ├── register.html           # Registration form
│   ├── dashboard.html          # Dashboard page
│   ├── profile.html            # Profile page
│   ├── analyze.html            # Opportunity text input form (Paste/Manual)
│   ├── analysis_result.html    # Full multi-score analysis report
│   ├── opportunities.html      # Filterable opportunity catalog
│   ├── opportunity_detail.html # Opportunity detail view
│   ├── applications.html       # Application tracker board
│   ├── application_detail.html # Application checklist & notes editor
│   └── settings.html           # Settings & integration roadmap
│
└── static/
    ├── css/
    │   └── style.css           # Modern mobile-first dark UI design system
    └── js/
        └── app.js              # Vanilla JS for interactive tags, tabs & AJAX
```

---

## 🧮 Multi-Dimensional Scoring Engine

OpportunityAI computes 4 core scores for every opportunity evaluated against a student's profile:

### 1. Personal Match Score (0–100%)
Calculated as a weighted composite of 6 transparent dimensions:
- **Eligibility match (25%)**: Degree, CGPA, and semester alignment.
- **Skills match (25%)**: Required vs. preferred skill overlap.
- **Education match (15%)**: Major and relevant coursework.
- **Interests match (15%)**: Alignment with user interest topics (e.g. AI/ML, Web Dev).
- **Experience match (10%)**: Stated project/internship experience.
- **Location match (10%)**: Remote, hybrid, or on-site preferences.

### 2. Urgency Score (0–100)
- **Critical (90–100)**: <= 3 days remaining or complex application requirements.
- **High (75–89)**: <= 7 days remaining.
- **Medium (50–74)**: <= 21 days remaining.
- **Low (0–49)**: > 21 days remaining.

### 3. Trust & Authenticity Indicator (0–100)
Evaluates positive signals (official domains, explicit contact info, structured eligibility) against negative signals (suspicious URLs, excessive claims, missing organization details).

### 4. Information Completeness Score (0–100%)
Checks presence of 11 critical information fields (Title, Org, Type, Description, Deadline, Location, Eligibility, Skills, Documents, Process, URL).

---

## ⚙️ How to Adjust Scoring Weights

You can adjust the scoring algorithm weights at any time in `config.py`:

```python
SCORING_WEIGHTS = {
    'eligibility': 0.25,
    'skills': 0.25,
    'education': 0.15,
    'interests': 0.15,
    'experience': 0.10,
    'location': 0.10,
}
```

---

## 🔐 Google Sign-In & Gmail Inbox Sync Setup

OpportunityAI can now sign students in with Google and read their Gmail (read-only)
to automatically find, score, and checklist opportunities buried in their inbox —
so nothing important gets lost in the noise of newsletters and promo emails.

To enable this, you need your own Google OAuth credentials (this app never ships
with shared credentials, for your own security):

### 1. Create OAuth credentials
1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Create a new project (or use an existing one)
3. Configure the **OAuth consent screen** (External type is fine for testing — add
   your own Google account as a test user)
4. Under **Scopes**, add:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
   - `https://www.googleapis.com/auth/gmail.readonly`
5. Create an **OAuth Client ID** → Application type: **Web application**
6. Add these **Authorized redirect URIs**:
   ```
   http://127.0.0.1:5000/auth/google/callback
   http://127.0.0.1:5000/gmail/callback
   ```
7. Copy the generated **Client ID** and **Client Secret**

### 2. Set environment variables
**Windows (Command Prompt):**
```bat
set GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
set GOOGLE_CLIENT_SECRET=your-client-secret
```
**Windows (PowerShell):**
```powershell
$env:GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_SECRET="your-client-secret"
```
**macOS/Linux:**
```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```
These need to be set in the *same terminal session* before you run `python app.py`.

### 3. (Recommended) Set a real token encryption key
Gmail refresh tokens are encrypted before being stored in the database. A dev-only
key is baked in as a fallback, but for anything beyond local testing, generate
your own:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
and set it:
```bash
export TOKEN_ENCRYPTION_KEY="paste-the-generated-key-here"
```

### 4. How it works
- **Sign in with Google** (`login.html` / `register.html`) — creates or links an
  account using just `openid email profile` scope. No Gmail access is requested here.
- **Connect Gmail** (Settings page or Inbox page) — a *separate*, explicit consent
  step that requests `gmail.readonly` + offline access, so students always know
  exactly when they're granting inbox access.
- **Sync Now** (Inbox page) — pulls recent messages matching opportunity-style
  keywords, runs them through a rule-based classifier (`services/classifier.py`)
  to filter out newsletters/promos/social noise, then feeds anything that passes
  through the same match/urgency/trust/completeness scoring engine used for
  manually-pasted opportunities (`services/pipeline.py`).
- Nothing is auto-tracked — synced opportunities sit in the Inbox for the student
  to **Track** or **Dismiss**. Tracking auto-generates the same interactive
  application checklist as manual entries.
- Sync is currently manual (a button), not scheduled in the background. Adding a
  periodic sync (e.g. with `APScheduler`) is a natural next step once this is
  working the way you want.

## 🔮 Future Integration & AI API Extension Point

The text analyzer service in `services/analyzer.py` is designed with an isolated entry point `analyze_opportunity(text)`.

When ready to connect an AI API (e.g. Gemini, OpenAI), set the environment variable:

```bash
export OPPORTUNITYAI_API_KEY="your-api-key-here"
```

The analyzer will route extraction requests to the external LLM while maintaining full fallback compatibility with the local Python rule-based engine.
