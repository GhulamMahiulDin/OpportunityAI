def ensure_profile_exists(db, user_id):
    """
    Guarantees a student_profiles row exists for this user, creating a
    blank one if it's somehow missing (e.g. an account created before a
    profile-creation code path existed, or a Google account linked to an
    old record). Safe to call on every request — INSERT OR IGNORE is a
    no-op if the row is already there.
    """
    db.execute(
        "INSERT OR IGNORE INTO student_profiles (user_id) VALUES (?)",
        (user_id,)
    )
    db.commit()


def get_profile(db, user_id):
    """
    Retrieves the student profile for a given user, including skills, interests, and preferences.
    """
    row = db.execute("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
        
    profile = dict(row)
    student_id = profile['id']
    
    profile['skills'] = get_student_skills(db, student_id)
    profile['interests'] = get_student_interests(db, student_id)
    profile['preferences'] = get_student_preferences(db, student_id)
    
    return profile

def update_profile(db, user_id, data_dict):
    """
    Updates the fields in student_profiles.
    """
    fields = ['university', 'degree', 'major', 'semester', 'cgpa', 'graduation_year', 'location', 'coursework', 'experience']
    updates = []
    values = []
    
    for field in fields:
        if field in data_dict:
            updates.append(f"{field} = ?")
            values.append(data_dict[field])
            
    if not updates:
        return
        
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(user_id)
    
    query = f"UPDATE student_profiles SET {', '.join(updates)} WHERE user_id = ?"
    db.execute(query, values)
    db.commit()

def add_skill(db, student_id, skill_name, proficiency='intermediate'):
    """
    Adds a skill to a student's profile.
    """
    db.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (skill_name,))
    skill_row = db.execute("SELECT id FROM skills WHERE name = ?", (skill_name,)).fetchone()
    
    if skill_row:
        skill_id = skill_row[0]
        db.execute(
            "INSERT OR IGNORE INTO student_skills (student_id, skill_id, proficiency) VALUES (?, ?, ?)",
            (student_id, skill_id, proficiency)
        )
        db.commit()

def remove_skill(db, student_id, skill_name):
    """
    Removes a skill from a student's profile.
    """
    skill_row = db.execute("SELECT id FROM skills WHERE name = ?", (skill_name,)).fetchone()
    if skill_row:
        db.execute(
            "DELETE FROM student_skills WHERE student_id = ? AND skill_id = ?",
            (student_id, skill_row[0])
        )
        db.commit()

def get_student_skills(db, student_id):
    """
    Retrieves all skills for a student.
    """
    rows = db.execute('''
        SELECT s.name, ss.proficiency 
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.id
        WHERE ss.student_id = ?
    ''', (student_id,)).fetchall()
    return [dict(r) for r in rows]

def add_interest(db, student_id, interest_name):
    """
    Adds an interest to a student's profile.
    """
    db.execute("INSERT OR IGNORE INTO interests (name) VALUES (?)", (interest_name,))
    interest_row = db.execute("SELECT id FROM interests WHERE name = ?", (interest_name,)).fetchone()
    
    if interest_row:
        db.execute(
            "INSERT OR IGNORE INTO student_interests (student_id, interest_id) VALUES (?, ?)",
            (student_id, interest_row[0])
        )
        db.commit()

def remove_interest(db, student_id, interest_name):
    """
    Removes an interest from a student's profile.
    """
    interest_row = db.execute("SELECT id FROM interests WHERE name = ?", (interest_name,)).fetchone()
    if interest_row:
        db.execute(
            "DELETE FROM student_interests WHERE student_id = ? AND interest_id = ?",
            (student_id, interest_row[0])
        )
        db.commit()

def get_student_interests(db, student_id):
    """
    Retrieves all interests for a student.
    """
    rows = db.execute('''
        SELECT i.name 
        FROM student_interests si
        JOIN interests i ON si.interest_id = i.id
        WHERE si.student_id = ?
    ''', (student_id,)).fetchall()
    return [r[0] for r in rows]

def add_preference(db, student_id, preference_name):
    """
    Adds a preference to a student's profile.
    """
    pref_row = db.execute("SELECT id FROM preferences WHERE name = ?", (preference_name,)).fetchone()
    if pref_row:
        db.execute(
            "INSERT OR IGNORE INTO student_preferences (student_id, preference_id) VALUES (?, ?)",
            (student_id, pref_row[0])
        )
        db.commit()

def remove_preference(db, student_id, preference_name):
    """
    Removes a preference from a student's profile.
    """
    pref_row = db.execute("SELECT id FROM preferences WHERE name = ?", (preference_name,)).fetchone()
    if pref_row:
        db.execute(
            "DELETE FROM student_preferences WHERE student_id = ? AND preference_id = ?",
            (student_id, pref_row[0])
        )
        db.commit()

def get_student_preferences(db, student_id):
    """
    Retrieves all preferences for a student.
    """
    rows = db.execute('''
        SELECT p.name, p.category 
        FROM student_preferences sp
        JOIN preferences p ON sp.preference_id = p.id
        WHERE sp.student_id = ?
    ''', (student_id,)).fetchall()
    
    result = {'types': [], 'formats': []}
    for r in rows:
        if r[1] == 'type':
            result['types'].append(r[0])
        elif r[1] == 'format':
            result['formats'].append(r[0])
    return result

def get_all_skills(db):
    """
    Retrieves all available skills.
    """
    rows = db.execute("SELECT name FROM skills ORDER BY name").fetchall()
    return [r[0] for r in rows]

def get_all_interests(db):
    """
    Retrieves all available interests.
    """
    rows = db.execute("SELECT name FROM interests ORDER BY name").fetchall()
    return [r[0] for r in rows]

def get_all_preferences(db):
    """
    Retrieves all available preferences grouped by category.
    """
    rows = db.execute("SELECT name, category FROM preferences ORDER BY name").fetchall()
    result = {'type': [], 'format': []}
    for r in rows:
        if r[1] in result:
            result[r[1]].append(r[0])
    return result
