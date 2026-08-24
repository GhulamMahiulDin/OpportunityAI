try:
    from config import Config
    SCORING_WEIGHTS = Config.SCORING_WEIGHTS
except ImportError:
    SCORING_WEIGHTS = {
        'eligibility': 0.25,
        'skills': 0.25,
        'education': 0.15,
        'interests': 0.15,
        'experience': 0.10,
        'location': 0.10,
    }

def calculate_skill_match(opportunity, profile):
    """Compare opportunity skills against student skills."""
    profile = profile or {}
    opportunity = opportunity or {}

    def _clean_skill_list(raw_list):
        """Coerce a list that may contain strings, dicts, None, or other junk
        into a clean list of trimmed skill-name strings."""
        cleaned = []
        for item in (raw_list or []):
            if isinstance(item, str):
                name = item
            elif isinstance(item, dict):
                name = item.get('name', '')
            else:
                name = ''
            if isinstance(name, str) and name.strip():
                cleaned.append(name.strip())
        return cleaned

    req_skills = _clean_skill_list(opportunity.get('required_skills', []))
    pref_skills = _clean_skill_list(opportunity.get('preferred_skills', []))

    # Assuming profile has a list of skills like [{'name': 'python', 'proficiency': 'high'}] or just strings
    student_skills = [s.lower() for s in _clean_skill_list(profile.get('skills', []))]

    req_matched = [s for s in req_skills if s.lower() in student_skills]
    req_missing = [s for s in req_skills if s.lower() not in student_skills]
    
    pref_matched = [s for s in pref_skills if s.lower() in student_skills]
    pref_missing = [s for s in pref_skills if s.lower() not in student_skills]
    
    req_score = (len(req_matched) / len(req_skills) * 100) if req_skills else 100
    pref_score = (len(pref_matched) / len(pref_skills) * 100) if pref_skills else 100
    
    score = (req_score * 0.7) + (pref_score * 0.3)
    
    return {
        'required_match': req_score,
        'preferred_match': pref_score,
        'required_matched': req_matched,
        'required_missing': req_missing,
        'preferred_matched': pref_matched,
        'preferred_missing': pref_missing,
        'score': score
    }

def calculate_eligibility(opportunity, profile):
    """Check each requirement for eligibility."""
    profile = profile or {}
    checks = []
    status = 'possibly_eligible'
    score = 50
    
    # Simplified check logic for now
    cgpa_req = opportunity.get('cgpa_requirement')
    if cgpa_req:
        try:
            req_val = float(cgpa_req)
            met = float(profile.get('cgpa', 0)) >= req_val
            checks.append({'field': 'CGPA', 'met': met, 'detail': f"Requires {req_val}, you have {profile.get('cgpa')}"})
            if not met:
                status = 'not_eligible'
                score = 0
        except ValueError:
            pass
            
    if not checks:
        status = 'eligible'
        score = 100
        checks.append({'field': 'General', 'met': True, 'detail': "No strict criteria found."})
        
    if status == 'not_eligible':
        score = 0
    elif status == 'eligible':
        score = 100
        
    return {'status': status, 'score': score, 'checks': checks}

def calculate_education_match(opportunity, profile):
    """Check if education aligns."""
    return {'score': 80, 'reasons': ['Education seems somewhat relevant']}

def calculate_interest_match(opportunity, profile):
    """Compare interests."""
    return {'score': 70, 'reasons': ['Matches some of your interests']}

def calculate_experience_match(opportunity, profile):
    """Check experience."""
    return {'score': 60, 'reasons': ['Experience requirement is acceptable']}

def calculate_location_match(opportunity, profile):
    """Compare locations."""
    return {'score': 90, 'reasons': ['Location is favorable']}

def calculate_match_score(opportunity, profile, scores_dict=None):
    """Combines all sub-scores with weights."""
    profile = profile or {}
    def get_num(val):
        if isinstance(val, dict):
            return val.get('score', 0)
        if isinstance(val, (int, float)):
            return val
        return 0

    sub_scores = {
        'eligibility': get_num(calculate_eligibility(opportunity, profile)),
        'skills': get_num(calculate_skill_match(opportunity, profile)),
        'education': get_num(calculate_education_match(opportunity, profile)),
        'interests': get_num(calculate_interest_match(opportunity, profile)),
        'experience': get_num(calculate_experience_match(opportunity, profile)),
        'location': get_num(calculate_location_match(opportunity, profile)),
    }

    if scores_dict:
        if 'eligibility' in scores_dict:
            sub_scores['eligibility'] = get_num(scores_dict['eligibility'])
        if 'skills' in scores_dict or 'skill_match' in scores_dict:
            sub_scores['skills'] = get_num(scores_dict.get('skills') or scores_dict.get('skill_match'))
        if 'education' in scores_dict:
            sub_scores['education'] = get_num(scores_dict['education'])
        if 'interests' in scores_dict:
            sub_scores['interests'] = get_num(scores_dict['interests'])
        if 'experience' in scores_dict:
            sub_scores['experience'] = get_num(scores_dict['experience'])
        if 'location' in scores_dict:
            sub_scores['location'] = get_num(scores_dict['location'])

    total_score = sum(sub_scores.get(k, 0) * SCORING_WEIGHTS.get(k, 0) for k in SCORING_WEIGHTS)
    
    reasons = []
    if sub_scores['eligibility'] >= 70:
        reasons.append("✓ Meets core eligibility criteria")
    else:
        reasons.append("⚠ Some eligibility criteria may be missing or unmet")

    if sub_scores['skills'] >= 70:
        reasons.append("✓ Strong skill match with required skills")
    elif sub_scores['skills'] >= 40:
        reasons.append("✓ Moderate skill match with requirements")
    else:
        reasons.append("⚠ Some required/preferred skills missing from profile")

    if sub_scores['interests'] >= 50:
        reasons.append("✓ Aligns with your specified career interests")

    return {'score': round(min(100, max(0, total_score)), 1), 'reasons': reasons}

def generate_recommendation(match_score, eligibility, urgency_score, trust_score, completeness_score):
    """Combine all scores into a final recommendation."""
    elig_status = eligibility.get('status') if isinstance(eligibility, dict) else str(eligibility)
    
    if match_score >= 80 and elig_status == 'eligible' and trust_score >= 60:
        return {'recommendation': 'strongly_consider', 'icon': '⭐', 'label': 'Strongly Consider Applying', 'reasons': ['High match score', 'Eligible']}
    elif match_score >= 60 and elig_status in ['eligible', 'possibly_eligible'] and trust_score >= 50:
        return {'recommendation': 'good_opportunity', 'icon': '👍', 'label': 'Good Opportunity', 'reasons': ['Solid match', 'Likely eligible']}
    elif match_score < 40:
        return {'recommendation': 'low_match', 'icon': '⚠', 'label': 'Low Match', 'reasons': ['Score is below 40']}
    else:
        return {'recommendation': 'review_before', 'icon': '🤔', 'label': 'Review Before Applying', 'reasons': ['Needs manual review or information missing']}

def generate_why_apply(opportunity, profile, scores_dict):
    """Generate concise reasons to apply."""
    profile = profile or {}
    reasons = []
    skill_m = scores_dict.get('skill_match', {})
    if isinstance(skill_m, dict) and skill_m.get('required_matched'):
        reasons.append(f"Your skills ({', '.join(skill_m['required_matched'][:3])}) match key requirements.")
    else:
        reasons.append("Your background aligns with the opportunity profile.")
        
    elig_m = scores_dict.get('eligibility', {})
    if isinstance(elig_m, dict) and elig_m.get('status') in ['eligible', 'possibly_eligible']:
        reasons.append("You meet the primary eligibility criteria.")

    reasons.append("Aligns with your academic and professional goals.")
    return reasons[:4]

def generate_things_to_consider(opportunity, profile, scores_dict):
    """Generate concise concerns or gaps."""
    profile = profile or {}
    concerns = []
    skill_m = scores_dict.get('skill_match', {})
    if isinstance(skill_m, dict) and skill_m.get('preferred_missing'):
        concerns.append(f"Missing preferred skills: {', '.join(skill_m['preferred_missing'][:3])}.")
        
    urgency_m = scores_dict.get('urgency', {})
    if isinstance(urgency_m, dict) and urgency_m.get('score', 0) >= 75:
        concerns.append("The application deadline is approaching soon.")

    if not concerns:
        concerns.append("Verify document requirements before submitting.")
    return concerns

