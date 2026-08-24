def calculate_completeness_score(opportunity):
    """
    Calculate how complete the opportunity information is.
    """
    fields_to_check = [
        ('title', 'Title'),
        ('organization', 'Organization'),
        ('description', 'Description (>50 chars)'),
        ('type', 'Type/Category'),
        ('eligibility_summary', 'Eligibility criteria'),
        ('deadline', 'Deadline'),
        ('location', 'Location'),
        ('required_skills', 'Requirements/skills'),
        ('required_documents', 'Required documents'),
        ('application_url', 'Application process/URL'),
        ('selection_process', 'Contact/selection info')
    ]
    
    present = []
    missing = []
    
    for key, name in fields_to_check:
        val = opportunity.get(key)
        is_present = False
        
        if key == 'description':
            is_present = bool(val and len(str(val)) > 50)
        elif key == 'required_skills':
            is_present = bool(val and len(val) > 0)
        else:
            is_present = bool(val and str(val).strip())
            
        if is_present:
            present.append({'field': name, 'detail': 'Provided'})
        else:
            missing.append({'field': name, 'suggestion': f'Try to find information about {name.lower()}'})
            
    fields_present = len(present)
    total_fields = len(fields_to_check)
    
    score = (fields_present / total_fields) * 100
    score = 100 if score >= 99 else int(score)
    
    return {
        'score': score,
        'present': present,
        'missing': missing,
        'total_fields': total_fields,
        'fields_present': fields_present
    }
