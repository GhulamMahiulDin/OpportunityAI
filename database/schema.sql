-- OpportunityAI Database Schema (PostgreSQL)
-- Converted from the original SQLite schema. Structure and semantics are
-- unchanged — only backend-specific syntax was translated:
--   INTEGER PRIMARY KEY AUTOINCREMENT  -> SERIAL PRIMARY KEY
--   INSERT OR IGNORE                    -> INSERT ... ON CONFLICT DO NOTHING

-- ============================================================
-- USERS & AUTHENTICATION
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    google_id TEXT UNIQUE,
    picture_url TEXT DEFAULT '',
    role TEXT NOT NULL DEFAULT 'student',   -- 'student' or 'admin'
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- STUDENT PROFILES
-- ============================================================

CREATE TABLE IF NOT EXISTS student_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    university TEXT DEFAULT '',
    degree TEXT DEFAULT '',
    major TEXT DEFAULT '',
    semester INTEGER DEFAULT 1,
    cgpa REAL DEFAULT 0.0,
    graduation_year INTEGER DEFAULT 2026,
    location TEXT DEFAULT '',
    coursework TEXT DEFAULT '',
    experience TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- SKILLS
-- ============================================================

CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS student_skills (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    proficiency TEXT DEFAULT 'intermediate',
    FOREIGN KEY (student_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    UNIQUE(student_id, skill_id)
);

-- ============================================================
-- INTERESTS
-- ============================================================

CREATE TABLE IF NOT EXISTS interests (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS student_interests (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    interest_id INTEGER NOT NULL,
    FOREIGN KEY (student_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (interest_id) REFERENCES interests(id) ON DELETE CASCADE,
    UNIQUE(student_id, interest_id)
);

-- ============================================================
-- PREFERENCES
-- ============================================================

CREATE TABLE IF NOT EXISTS preferences (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL  -- 'type' or 'format'
);

CREATE TABLE IF NOT EXISTS student_preferences (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    preference_id INTEGER NOT NULL,
    FOREIGN KEY (student_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (preference_id) REFERENCES preferences(id) ON DELETE CASCADE,
    UNIQUE(student_id, preference_id)
);

-- ============================================================
-- OPPORTUNITIES
-- ============================================================

CREATE TABLE IF NOT EXISTS opportunities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    organization TEXT DEFAULT '',
    type TEXT DEFAULT 'other',
    description TEXT DEFAULT '',
    location TEXT DEFAULT '',
    remote_onsite TEXT DEFAULT '',
    deadline TEXT DEFAULT '',
    application_url TEXT DEFAULT '',
    source_text TEXT DEFAULT '',
    eligibility_summary TEXT DEFAULT '',
    documents_needed TEXT DEFAULT '',
    selection_process TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    moderation_status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'flagged', 'removed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- OPPORTUNITY REQUIREMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS opportunity_requirements (
    id SERIAL PRIMARY KEY,
    opportunity_id INTEGER NOT NULL,
    requirement_type TEXT NOT NULL,       -- 'skill', 'degree', 'cgpa', 'experience', 'document', 'other'
    requirement_text TEXT NOT NULL,
    required_or_preferred TEXT DEFAULT 'required',  -- 'required' or 'preferred'
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
);

-- ============================================================
-- OPPORTUNITY SCORES (per student)
-- ============================================================

CREATE TABLE IF NOT EXISTS opportunity_scores (
    id SERIAL PRIMARY KEY,
    opportunity_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    match_score REAL DEFAULT 0,
    match_reasons TEXT DEFAULT '[]',
    eligibility_status TEXT DEFAULT 'unknown',
    eligibility_reasons TEXT DEFAULT '[]',
    skill_match_required REAL DEFAULT 0,
    skill_match_preferred REAL DEFAULT 0,
    skill_details TEXT DEFAULT '{}',
    urgency_score REAL DEFAULT 0,
    urgency_label TEXT DEFAULT 'Unknown',
    trust_score REAL DEFAULT 0,
    trust_reasons TEXT DEFAULT '[]',
    completeness_score REAL DEFAULT 0,
    completeness_details TEXT DEFAULT '{}',
    recommendation TEXT DEFAULT '',
    recommendation_icon TEXT DEFAULT '',
    why_apply TEXT DEFAULT '[]',
    things_to_consider TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
    UNIQUE(opportunity_id, student_id)
);

-- ============================================================
-- APPLICATIONS & TRACKING
-- ============================================================

CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    opportunity_id INTEGER NOT NULL,
    status TEXT DEFAULT 'saved',
    applied_at TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE,
    UNIQUE(student_id, opportunity_id)
);

CREATE TABLE IF NOT EXISTS application_tasks (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL,
    category TEXT DEFAULT 'general',
    task_name TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    due_date TEXT DEFAULT '',
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

-- ============================================================
-- ADMIN / SECURITY
-- ============================================================

-- Every admin action, for accountability (an audit trail).
CREATE TABLE IF NOT EXISTS admin_activity_logs (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,          -- e.g. 'DEACTIVATE_USER', 'DELETE_OPPORTUNITY', 'CORRECT_DEADLINE'
    target_type TEXT DEFAULT '',   -- e.g. 'user', 'opportunity'
    target_id INTEGER,
    details TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Login history, for security visibility (not behavioral tracking —
-- just login/logout/failed-attempt events, nothing about what a
-- student does inside the app).
CREATE TABLE IF NOT EXISTS login_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,               -- NULL for failed attempts against an unknown email
    email_attempted TEXT DEFAULT '',
    success INTEGER NOT NULL DEFAULT 1,
    ip_address TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- GMAIL INTEGRATION
-- ============================================================

CREATE TABLE IF NOT EXISTS gmail_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    gmail_address TEXT NOT NULL,
    encrypted_token TEXT NOT NULL,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Every Gmail message we've looked at, so we never re-process the same
-- email twice and can show the student what was found / skipped.
CREATE TABLE IF NOT EXISTS synced_emails (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    gmail_message_id TEXT NOT NULL,
    subject TEXT DEFAULT '',
    sender TEXT DEFAULT '',
    received_at TEXT DEFAULT '',
    classifier_score REAL DEFAULT 0,
    is_opportunity INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',   -- 'pending', 'reviewed', 'dismissed'
    opportunity_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL,
    UNIQUE(user_id, gmail_message_id)
);

-- ============================================================
-- SEED DATA: Default skills, interests, and preferences
-- ============================================================

INSERT INTO skills (name) VALUES
    ('Python'), ('C'), ('C++'), ('Java'), ('JavaScript'), ('HTML'), ('CSS'),
    ('SQL'), ('Flask'), ('Data Structures'), ('Algorithms'), ('Machine Learning'),
    ('AI'), ('Deep Learning'), ('TensorFlow'), ('PyTorch'), ('NLP'),
    ('Computer Vision'), ('Data Science'), ('Data Analysis'), ('Statistics'),
    ('R'), ('MATLAB'), ('Git'), ('Linux'), ('Docker'), ('AWS'),
    ('React'), ('Node.js'), ('UI/UX'), ('Figma'), ('Photoshop'),
    ('Excel'), ('Power BI'), ('Tableau'), ('MongoDB'), ('PostgreSQL'),
    ('Cybersecurity'), ('Networking'), ('Cloud Computing'),
    ('Android Development'), ('iOS Development'), ('Flutter'), ('Kotlin'),
    ('Swift'), ('Go'), ('Rust'), ('TypeScript'), ('PHP'), ('Ruby'),
    ('Communication'), ('Leadership'), ('Teamwork'), ('Problem Solving'),
    ('Project Management'), ('Research'), ('Technical Writing'),
    ('Public Speaking'), ('Critical Thinking')
ON CONFLICT (name) DO NOTHING;

INSERT INTO interests (name) VALUES
    ('AI/ML'), ('Web Development'), ('Software Engineering'), ('Data Science'),
    ('UI/UX'), ('Research'), ('Cybersecurity'), ('Cloud Computing'),
    ('Mobile Development'), ('Game Development'), ('Blockchain'),
    ('IoT'), ('Robotics'), ('Embedded Systems'), ('DevOps'),
    ('Competitive Programming'), ('Open Source'), ('Entrepreneurship'),
    ('Product Management'), ('Finance/Fintech'), ('Healthcare Tech'),
    ('Education Tech'), ('Social Impact'), ('Sustainability')
ON CONFLICT (name) DO NOTHING;

INSERT INTO preferences (name, category) VALUES
    ('Internship', 'type'), ('Scholarship', 'type'), ('Competition', 'type'),
    ('Fellowship', 'type'), ('Research', 'type'), ('Hackathon', 'type'),
    ('Job', 'type'), ('Workshop', 'type'), ('Conference', 'type'),
    ('Remote', 'format'), ('On-site', 'format'), ('Hybrid', 'format'),
    ('Local', 'format'), ('International', 'format')
ON CONFLICT (name) DO NOTHING;
