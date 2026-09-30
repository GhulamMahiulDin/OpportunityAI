import json

def create_opportunity(db, user_id, data_dict, source='manual'):
    """
    Creates a new opportunity. `source` is 'manual' (paste/manual entry
    on the Analyze page) or 'gmail' (auto-pulled from the student's inbox).
    """
    fields = ['user_id', 'source']
    values = [user_id, source]
    
    valid_keys = ['title', 'organization', 'type', 'description', 'location', 'remote_onsite', 
                  'deadline', 'application_url', 'source_text', 'eligibility_summary', 
                  'documents_needed', 'selection_process']
                  
    for k in valid_keys:
        if k in data_dict:
            fields.append(k)
            values.append(data_dict[k])
            
    query = f"INSERT INTO opportunities ({', '.join(fields)}) VALUES ({', '.join(['?' for _ in fields])})"
    cursor = db.execute(query, values)
    db.commit()
    return cursor.lastrowid

def get_opportunity(db, opportunity_id):
    """
    Retrieves an opportunity by ID.
    """
    row = db.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
    if row:
        return dict(row)
    return None

def get_opportunities_for_user(db, user_id, filters=None, student_id=None):
    """
    Retrieves opportunities created by a specific user with scores if available.
    """
    query = """
        SELECT o.*,
               COALESCE(os.match_score, 0) AS match_score,
               COALESCE(os.urgency_score, 0) AS urgency_score,
               os.urgency_label,
               COALESCE(os.trust_score, 0) AS trust_score,
               COALESCE(os.completeness_score, 0) AS completeness_score,
               os.recommendation
        FROM opportunities o
        LEFT JOIN opportunity_scores os
            ON o.id = os.opportunity_id AND os.student_id = ?
        WHERE o.user_id = ? AND o.moderation_status != 'removed'
    """
    params = [student_id, user_id]
    
    if filters:
        if filters.get('type'):
            query += " AND o.type = ?"
            params.append(filters['type'])
        if filters.get('search'):
            query += " AND (o.title LIKE ? OR o.organization LIKE ?)"
            search_term = f"%{filters['search']}%"
            params.extend([search_term, search_term])
            
    query += " ORDER BY o.created_at DESC"
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def update_opportunity(db, opportunity_id, data_dict):
    """
    Updates an opportunity.
    """
    valid_keys = ['title', 'organization', 'type', 'description', 'location', 'remote_onsite', 
                  'deadline', 'application_url', 'source_text', 'eligibility_summary', 
                  'documents_needed', 'selection_process']
                  
    updates = []
    values = []
    
    for k in valid_keys:
        if k in data_dict:
            updates.append(f"{k} = ?")
            values.append(data_dict[k])
            
    if not updates:
        return
        
    values.append(opportunity_id)
    query = f"UPDATE opportunities SET {', '.join(updates)} WHERE id = ?"
    db.execute(query, values)
    db.commit()

def delete_opportunity(db, opportunity_id):
    """
    Deletes an opportunity.
    """
    db.execute("DELETE FROM opportunities WHERE id = ?", (opportunity_id,))
    db.commit()

def add_requirement(db, opportunity_id, req_type, req_text, required_or_preferred='required'):
    """
    Adds a requirement to an opportunity.
    """
    db.execute(
        "INSERT INTO opportunity_requirements (opportunity_id, requirement_type, requirement_text, required_or_preferred) VALUES (?, ?, ?, ?)",
        (opportunity_id, req_type, req_text, required_or_preferred)
    )
    db.commit()

def get_requirements(db, opportunity_id):
    """
    Retrieves all requirements for an opportunity.
    """
    rows = db.execute("SELECT * FROM opportunity_requirements WHERE opportunity_id = ?", (opportunity_id,)).fetchall()
    return [dict(r) for r in rows]

def save_scores(db, opportunity_id, student_id, scores_dict):
    """
    Saves or updates scores for a specific opportunity and student.
    """
    # Convert dicts/lists to JSON strings
    json_fields = ['match_reasons', 'eligibility_reasons', 'skill_details', 'completeness_details', 'why_apply', 'things_to_consider']
    
    valid_keys = ['match_score', 'eligibility_status', 'skill_match_required', 'skill_match_preferred', 
                  'urgency_score', 'urgency_label', 'trust_score', 'completeness_score', 
                  'recommendation', 'recommendation_icon'] + json_fields
                  
    updates = []
    values = []
    insert_fields = ['opportunity_id', 'student_id']
    insert_values = [opportunity_id, student_id]
    insert_qs = ['?', '?']
    
    for k in valid_keys:
        if k in scores_dict:
            val = scores_dict[k]
            if k in json_fields and isinstance(val, (list, dict)):
                val = json.dumps(val)
                
            updates.append(f"{k} = ?")
            values.append(val)
            
            insert_fields.append(k)
            insert_values.append(val)
            insert_qs.append('?')
            
    # Check if exists
    exists = db.execute("SELECT id FROM opportunity_scores WHERE opportunity_id = ? AND student_id = ?", (opportunity_id, student_id)).fetchone()
    
    if exists:
        if updates:
            values.append(opportunity_id)
            values.append(student_id)
            query = f"UPDATE opportunity_scores SET {', '.join(updates)} WHERE opportunity_id = ? AND student_id = ?"
            db.execute(query, values)
    else:
        query = f"INSERT INTO opportunity_scores ({', '.join(insert_fields)}) VALUES ({', '.join(insert_qs)})"
        db.execute(query, insert_values)
        
    db.commit()

def get_scores(db, opportunity_id, student_id):
    """
    Retrieves scores for a specific opportunity and student.
    """
    row = db.execute("SELECT * FROM opportunity_scores WHERE opportunity_id = ? AND student_id = ?", (opportunity_id, student_id)).fetchone()
    
    if not row:
        return None
        
    result = dict(row)
    
    # Parse JSON fields
    json_fields = ['match_reasons', 'eligibility_reasons', 'skill_details', 'completeness_details', 'why_apply', 'things_to_consider']
    for k in json_fields:
        if result.get(k):
            try:
                result[k] = json.loads(result[k])
            except:
                result[k] = [] if k in ['match_reasons', 'eligibility_reasons', 'why_apply', 'things_to_consider'] else {}
                
    return result

def get_dashboard_data(db, user_id, student_id):
    """
    Retrieves dashboard summary data for a user.
    """
    total_opps = db.execute(
        "SELECT COUNT(*) FROM opportunities WHERE user_id = ? AND moderation_status != 'removed'",
        (user_id,)
    ).fetchone()[0]
    total_apps = db.execute("SELECT COUNT(*) FROM applications WHERE student_id = ?", (student_id,)).fetchone()[0]
    
    strong_matches = db.execute('''
        SELECT COUNT(*) FROM opportunity_scores os
        JOIN opportunities o ON os.opportunity_id = o.id
        WHERE o.user_id = ? AND os.student_id = ?
              AND o.moderation_status != 'removed'
              AND COALESCE(os.match_score, 0) >= 75
    ''', (user_id, student_id)).fetchone()[0]
    
    urgent = db.execute('''
        SELECT COUNT(*) FROM opportunity_scores os
        JOIN opportunities o ON os.opportunity_id = o.id
        WHERE o.user_id = ? AND os.student_id = ?
              AND o.moderation_status != 'removed'
              AND COALESCE(os.urgency_score, 0) >= 75
    ''', (user_id, student_id)).fetchone()[0]
    
    high_priority_rows = db.execute('''
        SELECT o.*, COALESCE(os.match_score, 0) AS match_score,
               COALESCE(os.urgency_score, 0) AS urgency_score,
               COALESCE(os.trust_score, 0) AS trust_score
        FROM opportunities o
        LEFT JOIN opportunity_scores os ON (o.id = os.opportunity_id AND os.student_id = ?)
        WHERE o.user_id = ? AND o.moderation_status != 'removed'
        ORDER BY COALESCE(os.match_score, 0) DESC, o.created_at DESC
        LIMIT 5
    ''', (student_id, user_id)).fetchall()
    
    return {
        'stats': {
            'total_opportunities': total_opps,
            'strong_matches': strong_matches,
            'urgent': urgent,
            'total_applications': total_apps
        },
        'high_priority': [dict(r) for r in high_priority_rows]
    }
