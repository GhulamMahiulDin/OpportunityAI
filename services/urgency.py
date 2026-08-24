from datetime import datetime
import re

def calculate_urgency_score(opportunity):
    """
    Calculate urgency score based on deadline and complexity.
    """
    deadline_str = opportunity.get('deadline')
    days_remaining = None
    score = 0
    label = 'Unknown'
    deadline_display = 'Not specified'
    details = []
    
    if deadline_str:
        try:
            # Basic parsing attempt
            # Assuming format might be YYYY-MM-DD for simplicity if parsed, or arbitrary string.
            # In a robust app, use dateutil or more formats.
            match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', deadline_str)
            if match:
                dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                days_remaining = (dt - datetime.now()).days
                deadline_display = dt.strftime('%Y-%m-%d')
        except Exception:
            pass
            
    if days_remaining is not None:
        if days_remaining < 0:
            score = 0
            label = 'Expired'
            details.append("The deadline has passed.")
        else:
            if days_remaining <= 3:
                score = 95
            elif days_remaining <= 7:
                score = 85
            elif days_remaining <= 14:
                score = 70
            elif days_remaining <= 21:
                score = 55
            elif days_remaining <= 30:
                score = 40
            else:
                score = 20
                
            details.append(f"{days_remaining} days remaining until deadline.")
    else:
        details.append("No valid deadline found.")
        
    docs = opportunity.get('documents_needed', '')
    if len(docs.split(',')) > 2:
        score += 10
        details.append("Requires multiple documents.")
        
    if 'recommendation' in docs.lower():
        score += 10
        details.append("Requires recommendation letters.")
        
    sel_process = opportunity.get('selection_process', '').lower()
    if 'test' in sel_process or 'interview' in sel_process:
        score += 5
        details.append("Selection process involves tests/interviews.")
        
    score = min(100, max(0, score))
    
    if label != 'Expired':
        if score >= 90: label = 'Critical'
        elif score >= 75: label = 'High'
        elif score >= 50: label = 'Medium'
        elif score > 0: label = 'Low'
        
    return {
        'score': score,
        'label': label,
        'days_remaining': days_remaining,
        'deadline_display': deadline_display,
        'details': details
    }
