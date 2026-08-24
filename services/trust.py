import re

def calculate_trust_score(opportunity):
    """
    Calculate a trust/authenticity score for an opportunity.
    """
    score = 0
    reasons = []
    
    org = opportunity.get('organization')
    if org and len(org.strip()) > 0:
        score += 15
        reasons.append({'type': 'positive', 'text': 'Has organization name'})
        
    url = opportunity.get('application_url', '')
    if url:
        score += 15
        reasons.append({'type': 'positive', 'text': 'Has application URL'})
        if 'https' in url.lower() and '.edu' in url.lower() or '.org' in url.lower() or '.gov' in url.lower():
            score += 10
            reasons.append({'type': 'positive', 'text': 'URL looks legitimate'})
        if 'bit.ly' in url.lower() or 'free' in url.lower():
            score -= 20
            reasons.append({'type': 'negative', 'text': 'Suspicious URL pattern'})
            
    if opportunity.get('deadline'):
        score += 10
        reasons.append({'type': 'positive', 'text': 'Has clear deadline'})
        
    desc = opportunity.get('description', '')
    if len(desc) > 100:
        score += 10
        reasons.append({'type': 'positive', 'text': 'Has detailed description'})
        
    if 'guaranteed' in desc.lower() or 'earn money fast' in desc.lower():
        score -= 15
        reasons.append({'type': 'negative', 'text': 'Suspicious language detected'})
    else:
        score += 10
        
    if 'bank' in desc.lower() or 'credit card' in desc.lower():
        score -= 30
        reasons.append({'type': 'negative', 'text': 'Asks for financial info'})
        
    if opportunity.get('location'):
        score += 5
        
    if opportunity.get('eligibility_summary'):
        score += 5
        
    if opportunity.get('selection_process'):
        score += 5
        
    score = min(100, max(0, score))
    
    if score >= 70:
        label = 'High confidence'
    elif score >= 40:
        label = 'Review carefully'
    else:
        label = 'Potential concerns'
        
    return {
        'score': score,
        'label': label,
        'reasons': reasons,
        'disclaimer': "This score identifies signals only and does not guarantee authenticity. Always verify through the organization's official website before submitting sensitive information."
    }
