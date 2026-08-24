import re
from datetime import datetime

def extract_title(text):
    """Extract opportunity title from text."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return ""
    
    # Check for subject lines
    for line in lines:
        if line.lower().startswith('subject:'):
            return line[8:].strip()
            
    # Return first prominent line, capped at 100 chars
    return lines[0][:100]

def extract_organization(text):
    """Extract organization name."""
    patterns = [
        r"(?i)organized by\s+([A-Z][\w\s&]+)",
        r"(?i)at\s+([A-Z][\w\s&]+University)",
        r"(?i)from\s+([A-Z][\w\s&]+Corp(?:oration)?|Inc\.?|LLC|Ltd\.?)",
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.group(1).strip()
    return ""

def classify_type(text):
    """Classify the opportunity type."""
    text_lower = text.lower()
    types = ['internship', 'scholarship', 'competition', 'fellowship', 'research', 'hackathon', 'job', 'workshop', 'conference']
    for t in types:
        if t in text_lower:
            return t
    return "other"

def extract_deadline(text):
    """Extract deadline as ISO string."""
    match = re.search(r"(?i)(?:deadline|apply by|due|closes|last date).*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})", text)
    if match:
        date_str = match.group(1)
        # Try to parse some basic formats
        try:
            # Let's try basic regex normalizations or return as is if complex
            return date_str
        except Exception:
            return date_str
    return ""

def extract_location(text):
    """Extract location."""
    match = re.search(r"(?i)(?:location|venue|where)\s*[:-]\s*([^.,\n]+)", text)
    if match:
        return match.group(1).strip()
    return ""

def extract_remote_onsite(text):
    """Classify as remote, on-site, or hybrid."""
    text_lower = text.lower()
    if 'hybrid' in text_lower:
        return 'hybrid'
    elif 'remote' in text_lower or 'work from home' in text_lower:
        return 'remote'
    elif 'on-site' in text_lower or 'onsite' in text_lower:
        return 'on-site'
    return ""

def extract_url(text):
    """Extract application URL."""
    match = re.search(r"(https?://[^\s]+)", text)
    if match:
        return match.group(1)
    return ""

def extract_skills(text):
    """Extract required and preferred skills."""
    skills_db = ['python', 'java', 'javascript', 'c++', 'html', 'css', 'sql', 'react', 'machine learning', 'data analysis']
    text_lower = text.lower()
    found_skills = [s for s in skills_db if s in text_lower]
    
    # Simplistic heuristic: if 'preferred' is near the skill, put it there, else required
    required = []
    preferred = []
    
    for s in found_skills:
        idx = text_lower.find(s)
        pref_idx = text_lower.find('prefer')
        if pref_idx != -1 and abs(pref_idx - idx) < 50:
            preferred.append(s)
        else:
            required.append(s)
            
    return required, preferred

def extract_documents(text):
    """Extract required documents."""
    docs_db = ['cv', 'resume', 'transcript', 'cover letter', 'motivation letter', 'recommendation', 'portfolio']
    text_lower = text.lower()
    found = [d for d in docs_db if d in text_lower]
    return ", ".join(found)

def extract_eligibility(text):
    """Extract eligibility criteria."""
    text_lower = text.lower()
    reqs = []
    if 'bachelor' in text_lower: reqs.append("Bachelor's degree")
    if 'master' in text_lower: reqs.append("Master's degree")
    
    cgpa_match = re.search(r"(?i)cgpa.*?(\d\.\d)", text_lower)
    if cgpa_match:
        reqs.append(f"Min CGPA: {cgpa_match.group(1)}")
        
    return "; ".join(reqs)

def extract_selection_process(text):
    """Extract selection process details."""
    processes = ['interview', 'assessment', 'test', 'screening']
    text_lower = text.lower()
    found = [p for p in processes if p in text_lower]
    return ", ".join(found)

def analyze_opportunity(text):
    """Analyze opportunity text and return structured data."""
    try:
        req_skills, pref_skills = extract_skills(text)
        
        return {
            'title': extract_title(text),
            'organization': extract_organization(text),
            'type': classify_type(text),
            'description': text[:500] + '...' if len(text) > 500 else text,
            'location': extract_location(text),
            'remote_onsite': extract_remote_onsite(text),
            'deadline': extract_deadline(text),
            'application_url': extract_url(text),
            'eligibility_summary': extract_eligibility(text),
            'required_skills': req_skills,
            'preferred_skills': pref_skills,
            'required_documents': extract_documents(text),
            'selection_process': extract_selection_process(text),
            'degree_requirement': '',
            'semester_requirement': '',
            'cgpa_requirement': '',
            'experience_requirement': '',
            'age_requirement': '',
            'country_restriction': ''
        }
    except Exception as e:
        return {'error': str(e)}

def analyze_opportunity_manual(data_dict):
    """Normalize manually entered structured data into the same format."""
    normalized = data_dict.copy()
    for key in ['required_skills', 'preferred_skills']:
        if isinstance(normalized.get(key), str):
            normalized[key] = [s.strip() for s in normalized[key].split(',') if s.strip()]
    return normalized
