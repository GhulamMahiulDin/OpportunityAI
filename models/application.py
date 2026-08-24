import sqlite3

def create_application(db, student_id, opportunity_id):
    """
    Creates a new application with status 'saved'.
    """
    cursor = db.execute(
        "INSERT INTO applications (student_id, opportunity_id, status) VALUES (?, ?, 'saved')",
        (student_id, opportunity_id)
    )
    db.commit()
    return cursor.lastrowid

def get_application_by_opportunity(db, student_id, opportunity_id):
    """
    Finds an existing application for a given student + opportunity pair, if any.
    """
    db.row_factory = sqlite3.Row
    row = db.execute(
        "SELECT * FROM applications WHERE student_id = ? AND opportunity_id = ?",
        (student_id, opportunity_id)
    ).fetchone()
    return dict(row) if row else None

def get_application(db, application_id):
    """
    Retrieves an application by ID, joined with its opportunity details
    and computed scores (field names match what the templates expect:
    title, organization, deadline, location, type, match_score, etc.)
    """
    db.row_factory = sqlite3.Row
    row = db.execute('''
        SELECT a.*, o.title, o.organization, o.deadline, o.location, o.type,
               o.application_url, o.description,
               os.match_score, os.urgency_score, os.trust_score, os.completeness_score
        FROM applications a
        JOIN opportunities o ON a.opportunity_id = o.id
        LEFT JOIN opportunity_scores os ON os.opportunity_id = o.id AND os.student_id = a.student_id
        WHERE a.id = ?
    ''', (application_id,)).fetchone()
    
    if row:
        return dict(row)
    return None

def get_applications_for_student(db, student_id, status_filter=None):
    """
    Retrieves applications for a student, optionally filtered by status.
    Field names match what the templates expect (title, organization,
    deadline, tasks_done, tasks_total) rather than raw SQL aliases.
    """
    db.row_factory = sqlite3.Row
    query = '''
        SELECT a.*, o.title, o.organization, o.deadline, o.location, o.type,
               os.match_score, os.urgency_score,
               (SELECT COUNT(*) FROM application_tasks t WHERE t.application_id = a.id AND t.completed = 1) as tasks_done,
               (SELECT COUNT(*) FROM application_tasks t WHERE t.application_id = a.id) as tasks_total
        FROM applications a
        JOIN opportunities o ON a.opportunity_id = o.id
        LEFT JOIN opportunity_scores os ON o.id = os.opportunity_id AND os.student_id = a.student_id
        WHERE a.student_id = ?
    '''
    params = [student_id]
    
    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)
        
    query += " ORDER BY a.updated_at DESC"
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]

def update_application_status(db, application_id, status):
    """
    Updates the status of an application.
    """
    db.execute(
        "UPDATE applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, application_id)
    )
    db.commit()

def update_application_notes(db, application_id, notes):
    """
    Updates the notes of an application.
    """
    db.execute(
        "UPDATE applications SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (notes, application_id)
    )
    db.commit()

def add_task(db, application_id, category, task_name, due_date=''):
    """
    Adds a task to an application.
    """
    db.execute(
        "INSERT INTO application_tasks (application_id, category, task_name, due_date) VALUES (?, ?, ?, ?)",
        (application_id, category, task_name, due_date)
    )
    db.commit()

def get_tasks(db, application_id):
    """
    Retrieves all tasks for an application.
    """
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT * FROM application_tasks WHERE application_id = ?", (application_id,)).fetchall()
    return [dict(r) for r in rows]

def toggle_task(db, task_id):
    """
    Toggles the completed status of a task. Returns the new completed
    state (True/False), or None if the task doesn't exist.
    """
    row = db.execute("SELECT completed FROM application_tasks WHERE id = ?", (task_id,)).fetchone()
    if row:
        new_status = 1 if row[0] == 0 else 0
        db.execute("UPDATE application_tasks SET completed = ? WHERE id = ?", (new_status, task_id))
        db.commit()
        return bool(new_status)
    return None

def delete_application(db, application_id):
    """
    Deletes an application and its tasks.
    """
    db.execute("DELETE FROM applications WHERE id = ?", (application_id,))
    db.commit()

def generate_checklist_from_opportunity(db, application_id, opportunity_id):
    """
    Generates a checklist for an application based on opportunity requirements.
    """
    db.row_factory = sqlite3.Row
    opportunity = db.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
    requirements = db.execute("SELECT * FROM opportunity_requirements WHERE opportunity_id = ?", (opportunity_id,)).fetchall()
    
    if not opportunity:
        return
        
    tasks = []
    
    # Eligibility
    tasks.append(('eligibility', 'Verify eligibility criteria', ''))
    
    # Documents
    documents = [req['requirement_text'] for req in requirements if req['requirement_type'] == 'document']
    if documents:
        for doc in documents:
            tasks.append(('documents', f'Prepare {doc}', ''))
    else:
        # Check opportunity text fields for clues
        if opportunity['documents_needed']:
            tasks.append(('documents', 'Review required documents', ''))
        else:
            tasks.append(('documents', 'Update resume', ''))
            
    # Application
    tasks.append(('application', 'Fill out application form', opportunity['deadline'] or ''))
    tasks.append(('application', 'Submit application', opportunity['deadline'] or ''))
    
    # After Applying
    tasks.append(('after_applying', 'Save copy of application', ''))
    
    # Insert tasks
    for category, name, due_date in tasks:
        add_task(db, application_id, category, name, due_date)
