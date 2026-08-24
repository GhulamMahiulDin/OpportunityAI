import os
import sys
import psycopg2
import psycopg2.extras
import json
from config import Config
from database.db import PGConnectionWrapper
from models.user import create_user, get_user_by_email, ensure_super_admin
from models.profile import (
    get_profile, update_profile, add_skill, add_interest, add_preference
)
from models.opportunity import create_opportunity, add_requirement, save_scores
from models.application import create_application, generate_checklist_from_opportunity
from services.analyzer import analyze_opportunity
from services.scoring import (
    calculate_match_score, calculate_skill_match, calculate_eligibility,
    generate_recommendation, generate_why_apply, generate_things_to_consider
)
from services.urgency import calculate_urgency_score
from services.trust import calculate_trust_score
from services.completeness import calculate_completeness_score

DEMO_OPPORTUNITIES = [
    # --- 3 INTERNSHIPS ---
    {
        "title": "Software Engineering Summer Intern 2026",
        "organization": "Google",
        "type": "internship",
        "raw_text": """
Subject: Google Software Engineering Internship 2026 - Applications Now Open

Google is hiring Software Engineering Interns for Summer 2026 in Mountain View, CA and Remote locations!

About the Role:
As a SWE Intern, you will work on core Google systems using Python, C++, and Web technologies. You'll collaborate with senior software engineers on scalable infrastructure, cloud services, and machine learning models.

Requirements:
- Currently enrolled in a Bachelor's or Master's degree in Computer Science or related STEM field.
- Expected graduation date between December 2026 and June 2027 (Semester 5-7).
- Minimum CGPA of 3.3 / 4.0.
- Proficiency in Python, C++, or Java, and solid knowledge of Data Structures and Algorithms.
- Familiarity with SQL, Git, and Web Development is preferred.

Location: Remote / Mountain View, CA (Hybrid options available)
Stipend: $52/hr + housing stipend

Application Process:
1. Online Application with Resume & Transcript
2. Online Coding Assessment (Algorithms & Data Structures)
3. Technical Interviews (2 rounds)

Required Documents: Updated CV / Resume, Official Transcript
Deadline: September 15, 2026
Apply URL: https://careers.google.com/jobs/results/swe-intern-2026
Contact: university-recruiting@google.com
"""
    },
    {
        "title": "Machine Learning & AI Research Intern",
        "organization": "OpenAI Labs",
        "type": "internship",
        "raw_text": """
Subject: OpenAI Summer 2026 Student Research Internship

OpenAI is seeking passionate undergraduate and graduate student researchers for our Summer 2026 Cohort.

Scope of Work:
You will design, implement, and evaluate deep learning experiments in Large Language Models, Computer Vision, and Reinforcement Learning.

Eligibility Criteria:
- Enrolled in Computer Science, Data Science, or Artificial Intelligence degree program.
- Strong proficiency in Python, PyTorch, TensorFlow, and Data Structures.
- Coursework or experience in Machine Learning, Deep Learning, and Linear Algebra.
- CGPA >= 3.5 preferred.

Benefits:
- Competitive stipend ($60/hr)
- Mentorship from leading AI researchers
- Publication opportunities in top AI conferences (NeurIPS, ICML)

Required Documents: CV, Cover Letter, Academic Transcript, Code Sample / GitHub Link
Deadline: October 1, 2026
Apply Link: https://openai.com/careers/research-intern-2026
Selection Process: Resume Screening -> Coding Test -> Technical Interview -> Final Offer
"""
    },
    {
        "title": "Full Stack Web Development Intern",
        "organization": "Stripe Tech",
        "type": "internship",
        "raw_text": """
Subject: Stripe Fall 2026 Engineering Internship Program

Stripe is opening applications for Full Stack Web Engineering Interns.

Responsibilities:
Build developer-friendly APIs, responsive dashboards, and robust web applications using JavaScript, HTML, CSS, Flask/Python, and SQL databases.

Requirements:
- Pursuing Bachelor's degree in Computer Science or Software Engineering.
- Practical experience with JavaScript, HTML, CSS, Python, and SQL.
- Understanding of web security and clean code practices.
- Remote work allowed within US, UK, and Canada.

Application Deadline: August 28, 2026
Apply Portal: https://stripe.com/jobs/intern-web-dev
Required Documents: Resume, Portfolio or GitHub link
Process: Online application, Technical assessment, Pair programming interview
"""
    },

    # --- 3 SCHOLARSHIPS ---
    {
        "title": "Global Tech Excellence & AI Leaders Scholarship 2026",
        "organization": "Google & Udacity Foundation",
        "type": "scholarship",
        "raw_text": """
Announcement: 2026 Global Tech Excellence & AI Leaders Scholarship Fund

The Global Tech Foundation is offering $10,000 tuition scholarships for high-achieving undergraduate students majoring in Computer Science, AI/ML, or Software Engineering.

Award Amount: $10,000 direct tuition grant + 1-year free access to Nanodegree programs.

Eligibility:
- Currently enrolled full-time student in Semester 3 to Semester 8.
- CGPA of 3.20 or higher.
- Demonstrated passion for Technology, Open Source, or Artificial Intelligence.
- International students welcome to apply.

Required Documents:
- Academic Transcript
- Motivation Letter / Personal Statement (500 words)
- 2 Letters of Recommendation from Professors
- CV / Resume

Selection Process:
1. Document Review
2. Virtual Panel Interview

Deadline: September 30, 2026
Official Portal: https://globaltechfoundation.org/scholarship-2026
"""
    },
    {
        "title": "Women & Allies in Computer Science Scholarship",
        "organization": "Anita Borg Institute",
        "type": "scholarship",
        "raw_text": """
Opportunity: AnitaB.org Computer Science Innovation Grant 2026

Grant Amount: $5,000 + Sponsored Ticket to Grace Hopper Celebration 2026.

Eligibility & Criteria:
- Enrolled in Bachelor's or Master's in CS, IT, or Data Science.
- Active involvement in community tech initiatives or campus tech clubs.
- Skills in Python, Java, or Web Development appreciated.

Requirements:
- Resume
- Transcript
- Recommendation Letter
- Short Essay on "How I Plan to Impact the Tech Industry"

Deadline: October 15, 2026
URL: https://anitab.org/scholarships/2026-grant
"""
    },
    {
        "title": "Cybersecurity & Software Trust Academic Grant",
        "organization": "Linux Foundation",
        "type": "scholarship",
        "raw_text": """
Linux Foundation Student Academic Grant for Open Source Security

The Linux Foundation is providing 50 student grants of $3,000 each to support students studying Cybersecurity, Linux kernel development, or Secure Software Engineering.

Criteria:
- Enrolled STEM university student.
- Knowledge of C, C++, Python, or Linux environment.

Deadline: November 1, 2026
Application URL: https://linuxfoundation.org/grants/student-2026
Documents: CV, Motivation Letter
"""
    },

    # --- 2 COMPETITIONS ---
    {
        "title": "ACM Global Student Algorithmic Code Challenge 2026",
        "organization": "ACM & Codeforces",
        "type": "competition",
        "raw_text": """
Announcing: ACM Global Algorithmic & Data Structures Championship 2026

Compete against top university coders worldwide! Solve complex algorithmic challenges using C++, Python, or Java.

Prizes:
- 1st Place: $15,000 + Tech Conference Trip
- Top 50: Cash prizes + direct interview invites from top tech firms

Eligibility:
- Undergraduate or Graduate students registered at accredited universities.
- Mastery of Data Structures, Algorithms, Graph Theory, and Dynamic Programming.

Timeline:
- Qualification Round: September 10, 2026
- Final Round: September 25, 2026

Registration URL: https://acm-codechallenge2026.org/register
Required: Student ID verification, Codeforces/LeetCode profile
Deadline: September 8, 2026
"""
    },
    {
        "title": "Generative AI & Web Innovation Hackathon",
        "organization": "Microsoft & GitHub",
        "type": "competition",
        "raw_text": """
Hackathon Alert: Microsoft GenAI & Web Hackathon 2026 (Virtual)

Build innovative web applications powered by Generative AI and LLMs in 48 hours!

Prize Pool: $30,000 in Azure credits and cash prizes.

Skills Needed: Python, Flask/FastAPI, JavaScript, HTML, CSS, OpenAI API / Azure AI services.

Format: Virtual / Online Hackathon (Teams of 1-4 students)
Deadline to Register: March 1, 2026
Submission URL: https://genai-hackathon2026.devpost.com
Documents required: Project Pitch, Demo Video, GitHub Repository
"""
    },

    # --- 2 RESEARCH OPPORTUNITIES ---
    {
        "title": "Undergraduate AI & NLP Student Research Fellowship",
        "organization": "Stanford NLP Group",
        "type": "research",
        "raw_text": """
Call for Student Researchers: Stanford NLP & Machine Intelligence Lab

The Stanford NLP Lab invites applications from visiting and remote undergraduate research assistants for Fall 2026.

Research Focus: Efficient Large Language Models, Multi-modal Learning, and Machine Translation.

Prerequisites:
- Strong background in Python, PyTorch/TensorFlow, Linear Algebra, and NLP concepts.
- Preferred CGPA: 3.7 / 4.0+.
- Prior research experience or strong project portfolio in Machine Learning.

Benefits: $4,000/month research stipend + co-authorship on lab papers.
Deadline: September 20, 2026
Application URL: https://nlp.stanford.edu/research-fellowship-2026
Required Docs: Academic CV, Statement of Research Intent, 2 Recommendation Letters
"""
    },
    {
        "title": "Web Systems & Distributed Databases Research Project",
        "organization": "MIT Computer Science Lab (CSAIL)",
        "type": "research",
        "raw_text": """
MIT CSAIL Undergraduate Research Opportunity (URO)

Work directly with MIT faculty on high-performance distributed databases and secure SQL engines.

Requirements:
- Proficiency in C, C++, Python, and SQL database internal concepts.
- Understanding of Data Structures and Operating Systems concepts.

Duration: 6 months (Remote/Hybrid)
Stipend: $3,500/month
Deadline: October 5, 2026
Apply Link: https://csail.mit.edu/uro-database-2026
Required Documents: Resume, Academic Transcript, Cover Letter
"""
    },

    # --- 1 FELLOWSHIP ---
    {
        "title": "Schwarzman Global Leadership & Technology Fellowship",
        "organization": "Schwarzman Scholars Foundation",
        "type": "fellowship",
        "raw_text": """
Schwarzman Global Tech & Policy Fellowship 2026-2027

A fully-funded 1-year fellowship designed for future technology leaders, innovators, and software developers.

Covers:
- 100% Tuition & Fees
- Room & Board
- Travel Stipend & $4,000 annual allowance

Eligibility:
- Bachelor's degree or expected graduation by June 2027.
- Age 18-28.
- Demonstrated leadership potential, strong academic record (CGPA >= 3.4), and technical or analytical background.

Required Documents:
- Complete Resume / CV
- 3 Recommendation Letters
- 2 Essays (Leadership & Statement of Purpose)
- Official Transcripts

Deadline: October 30, 2026
Application URL: https://schwarzmanscholars.org/apply-2026
Selection: Application -> Regional Interview -> Final Selection Announcement
"""
    }
]

def _parse_database_url(url):
    """Breaks a postgresql:// connection string into its components."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'user': parsed.username or 'postgres',
        'password': parsed.password or '',
        'dbname': (parsed.path or '/postgres').lstrip('/') or 'postgres',
    }


def _connect_maintenance_db():
    """
    Connects to the 'postgres' maintenance database (not the app database)
    on the SAME server/credentials as Config.DATABASE_URL, used only to
    check for / create the target database on a local PostgreSQL install
    you control.
    """
    components = _parse_database_url(Config.DATABASE_URL)
    return psycopg2.connect(
        host=components['host'], port=components['port'],
        user=components['user'], password=components['password'],
        dbname='postgres'
    )


def _ensure_database_exists():
    """
    Best-effort: auto-creates the target database if it's missing, which
    works when you control the Postgres server yourself (a local install,
    or your own VM). On hosted providers — Supabase, Render Postgres,
    Railway, etc. — the database already exists and your app user
    typically doesn't have permission to create new ones (and shouldn't
    need to). That's expected there, not an error, so failures here are
    reported and then execution continues on the assumption the target
    database already exists.
    """
    target_dbname = _parse_database_url(Config.DATABASE_URL)['dbname']
    try:
        conn = _connect_maintenance_db()
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_dbname,))
        exists = cur.fetchone() is not None
        if not exists:
            print(f"Creating database '{target_dbname}'...")
            cur.execute(f'CREATE DATABASE "{target_dbname}"')
        cur.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"(Skipping auto-create check: {str(e).strip()})")
        print(" This is normal on hosted PostgreSQL (Supabase, Render, Railway, etc.) —")
        print(" the database already exists there and your user usually can't create")
        print(" new ones. Continuing on the assumption the target database already exists.\n")


def init_db(force=False):
    db_info = _parse_database_url(Config.DATABASE_URL)
    print("Initializing OpportunityAI PostgreSQL database...")
    print(f"Target: {db_info['user']}@{db_info['host']}:{db_info['port']}/{db_info['dbname']}")

    _ensure_database_exists()

    try:
        raw_conn = psycopg2.connect(
            Config.DATABASE_URL,
            cursor_factory=psycopg2.extras.DictCursor
        )
    except psycopg2.OperationalError as e:
        print("\n" + "!" * 70)
        print("! Could not connect to the target database:")
        print(f"!   {db_info['user']}@{db_info['host']}:{db_info['port']}/{db_info['dbname']}")
        print("!")
        print(f"! {str(e).strip()}")
        print("!")
        print("! If you're using a hosted provider (Supabase, Render, Railway, etc.),")
        print("! make sure the database itself has already been created/provisioned")
        print("! in their dashboard first — this script can only auto-create a")
        print("! database when it has permission to (typical for local PostgreSQL,")
        print("! not typical for hosted providers). Double-check your DATABASE_URL")
        print("! is exactly what your provider gave you.")
        print("!" * 70 + "\n")
        sys.exit(1)

    check_cur = raw_conn.cursor()
    check_cur.execute("SELECT to_regclass('public.users')")
    already_has_schema = check_cur.fetchone()['to_regclass'] is not None
    check_cur.close()

    if already_has_schema:
        if not force:
            print("\n" + "!" * 70)
            print("! Tables already exist in this database:")
            print(f"!   {Config.PGDATABASE} on {Config.PGHOST}:{Config.PGPORT}")
            print("! Running this WILL DELETE all users, profiles, applications,")
            print("! opportunities, Gmail connections, and synced email history.")
            print("!" * 70)
            answer = input("Type 'yes' to drop everything and start fresh, anything else to cancel: ").strip().lower()
            if answer != 'yes':
                print("Cancelled. Your existing database was left untouched.")
                raw_conn.close()
                return
        reset_cur = raw_conn.cursor()
        reset_cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        raw_conn.commit()
        reset_cur.close()

    conn = PGConnectionWrapper(raw_conn)

    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(__file__), 'database', 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()

    print("Schema created. Populating seed demo user and profile...")

    # Create demo user
    user_id = create_user(conn, "Alex Chen", "demo@opportunityai.org", "password123")
    conn.commit()

    # Create demo admin account (for testing the Admin Portal).
    # Credentials come from ADMIN_EMAIL / ADMIN_PASSWORD environment
    # variables when set, so production deployments never rely on a
    # hard-coded admin password. A dev-only fallback is used (and loudly
    # flagged) so local `python init_db.py` still works out of the box.
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    using_dev_admin_fallback = not admin_email or not admin_password
    if using_dev_admin_fallback:
        admin_email = admin_email or 'admin@opportunityai.org'
        admin_password = admin_password or 'adminpass123'

    admin_id = create_user(conn, "Admin", admin_email, admin_password)
    conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (admin_id,))
    conn.commit()

    # Ensure the permanent Super Admin account exists (idempotent —
    # never duplicates the account or overwrites an existing password).
    ensure_super_admin(conn)
    conn.commit()

    # Get student profile
    profile = get_profile(conn, user_id)
    student_id = profile['id']

    # Update student profile with strong details
    update_profile(conn, user_id, {
        'university': 'State Tech University',
        'degree': "Bachelor's",
        'major': 'Computer Science',
        'semester': 6,
        'cgpa': 3.75,
        'graduation_year': 2027,
        'location': 'New York, USA',
        'coursework': 'Data Structures, Algorithms, Database Systems, Web Development, Machine Learning, Operating Systems',
        'experience': '6-month Web Development project, Machine Learning coursework project using Python & SQL'
    })

    # Add student skills
    demo_skills = [
        'Python', 'C', 'C++', 'JavaScript', 'HTML', 'CSS',
        'Flask', 'SQL', 'Data Structures', 'Algorithms',
        'Git', 'UI/UX', 'Machine Learning', 'Data Analysis'
    ]
    for skill in demo_skills:
        add_skill(conn, student_id, skill)

    # Add student interests
    demo_interests = ['AI/ML', 'Web Development', 'Software Engineering', 'Research']
    for interest in demo_interests:
        add_interest(conn, student_id, interest)

    # Add student preferences
    demo_prefs = [
        'Internship', 'Scholarship', 'Competition', 'Fellowship', 'Research',
        'Remote', 'Hybrid', 'On-site'
    ]
    for pref in demo_prefs:
        add_preference(conn, student_id, pref)

    conn.commit()
    print(f"Demo profile created for student (ID: {student_id}). Analyzing sample opportunities...")

    # Fetch updated profile for scoring engine
    updated_profile = get_profile(conn, user_id)

    # Insert demo opportunities and compute full scores
    created_opp_ids = []
    for i, item in enumerate(DEMO_OPPORTUNITIES):
        extracted = analyze_opportunity(item['raw_text'])
        # Ensure title/org/type fallback if needed
        extracted['title'] = item['title']
        extracted['organization'] = item['organization']
        extracted['type'] = item['type']

        opp_id = create_opportunity(conn, user_id, extracted)
        created_opp_ids.append(opp_id)
        # Seed/demo content is trusted (we wrote it), so auto-approve it —
        # new opportunities created by students/Gmail sync still default
        # to 'pending' per the schema until an admin reviews them.
        conn.execute("UPDATE opportunities SET moderation_status = 'approved' WHERE id = ?", (opp_id,))

        # Requirements
        for skill in extracted.get('required_skills', []):
            add_requirement(conn, opp_id, 'skill', skill, 'required')
        for skill in extracted.get('preferred_skills', []):
            add_requirement(conn, opp_id, 'skill', skill, 'preferred')
        for doc in extracted.get('required_documents', []):
            add_requirement(conn, opp_id, 'document', doc, 'required')

        # Run scoring
        skill_match_res = calculate_skill_match(extracted, updated_profile)
        eligibility_res = calculate_eligibility(extracted, updated_profile)
        urgency_res = calculate_urgency_score(extracted)
        trust_res = calculate_trust_score(extracted)
        completeness_res = calculate_completeness_score(extracted)

        temp_scores = {
            'skill_match': skill_match_res,
            'eligibility': eligibility_res,
            'urgency': urgency_res,
            'trust': trust_res,
            'completeness': completeness_res
        }

        match_res = calculate_match_score(extracted, updated_profile, temp_scores)

        rec_res = generate_recommendation(
            match_res['score'],
            eligibility_res['status'],
            urgency_res['score'],
            trust_res['score'],
            completeness_res['score']
        )

        why_apply = generate_why_apply(extracted, updated_profile, temp_scores)
        things_to_consider = generate_things_to_consider(extracted, updated_profile, temp_scores)

        final_scores = {
            'match_score': match_res['score'],
            'match_reasons': match_res['reasons'],
            'eligibility_status': eligibility_res['status'],
            'eligibility_reasons': [c['detail'] for c in eligibility_res['checks']],
            'skill_match_required': skill_match_res['required_match'],
            'skill_match_preferred': skill_match_res['preferred_match'],
            'skill_details': skill_match_res,
            'urgency_score': urgency_res['score'],
            'urgency_label': urgency_res['label'],
            'trust_score': trust_res['score'],
            'trust_reasons': trust_res['reasons'],
            'completeness_score': completeness_res['score'],
            'completeness_details': completeness_res,
            'recommendation': rec_res['recommendation'],
            'recommendation_label': rec_res['label'],
            'recommendation_icon': rec_res['icon'],
            'why_apply': why_apply,
            'things_to_consider': things_to_consider,
            'days_remaining': urgency_res.get('days_remaining'),
            'trust_label': trust_res.get('label'),
            'trust_disclaimer': trust_res.get('disclaimer'),
            'eligibility_checks': eligibility_res.get('checks', []),
            'completeness_present': completeness_res.get('fields_present', 0),
            'completeness_total': completeness_res.get('total_fields', 11),
            'completeness_present_items': completeness_res.get('present', []),
            'completeness_missing_items': completeness_res.get('missing', [])
        }

        save_scores(conn, opp_id, student_id, final_scores)

    conn.commit()
    print(f"Created {len(created_opp_ids)} sample opportunities with transparent scores.")

    # Create sample applications for tracker
    # Save the first 3 opportunities into Applications tracker
    for opp_id in created_opp_ids[:3]:
        app_id = create_application(conn, student_id, opp_id)
        generate_checklist_from_opportunity(conn, app_id, opp_id)

    conn.commit()
    conn.close()
    print("Database initialization complete! Sample logins:")
    print("  Student — Email: demo@opportunityai.org   Password: password123")
    if using_dev_admin_fallback:
        print(f"  Admin   — Email: {admin_email}  Password: {admin_password}")
        print("\n" + "!" * 70)
        print("! WARNING: The admin account above uses a DEV-ONLY DEFAULT password.")
        print("! Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables before")
        print("! running init_db.py again for anything other than local testing.")
        print("!" * 70)
    else:
        print(f"  Admin   — Email: {admin_email}  (password set via ADMIN_PASSWORD env var)")
    print(f"  Super Admin — Email: {Config.SUPER_ADMIN_EMAIL}  (see warning above if SUPER_ADMIN_PASSWORD was unset)")
    print("\nNote: these demo accounts exist for local testing/demonstration.")
    print("If you ever deploy this app somewhere public, delete them or change")
    print("their passwords first — these should never reach production.\n")

if __name__ == '__main__':
    import sys
    force = '--force' in sys.argv or '-f' in sys.argv
    init_db(force=force)
