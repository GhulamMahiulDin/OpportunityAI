"""
Rule-based "is this email actually an opportunity worth my time?" gate.

This runs BEFORE the full analyzer/scoring pipeline. Its only job is to
cheaply separate genuine internship/scholarship/competition/research/job
emails from the huge volume of newsletters, promos, and social noise that
fill a student's inbox — so we only run the heavier analysis on emails
that are actually worth it.
"""
import re

POSITIVE_KEYWORDS = [
    'internship', 'scholarship', 'fellowship', 'hackathon', 'competition',
    'call for applications', 'apply now', 'apply here', 'apply by',
    'application deadline', 'research opportunity', 'traineeship',
    'graduate program', 'summer program', 'volunteer program',
    'job opening', 'position available', 'we are hiring', 'now hiring',
    'eligib', 'stipend', 'grant opportunity', 'call for papers',
    'request for proposals', 'exchange program', 'bootcamp',
]

DEADLINE_PATTERNS = [
    r'\bdeadline\b', r'\bapply by\b', r'\bdue date\b', r'\bcloses on\b',
    r'\blast date\b', r'\bsubmission deadline\b',
]

NEGATIVE_KEYWORDS = [
    'unsubscribe', '% off', 'percent off', 'discount code', 'flash sale',
    'buy now', 'limited time offer', 'coupon', 'free shipping',
    'liked your post', 'commented on your', 'tagged you', 'friend request',
    'new follower', 'your weekly digest', 'watch now', 'new episode',
    'order confirmation', 'your receipt', 'payment received',
    'verify your account', 'password reset', 'security alert',
]

TRUSTED_SENDER_HINTS = ['.edu', '.ac.', '.gov', 'noreply@', 'careers@', 'internships@', 'admissions@']


def classify_email(subject, body, sender=''):
    """
    Scores an email 0-100 on how likely it is to be a genuine opportunity
    (internship/scholarship/competition/fellowship/research/job posting).

    Returns: {'score': int, 'is_opportunity': bool, 'signals': [str, ...]}
    """
    text = f"{subject}\n{body}".lower()
    sender_lower = sender.lower()
    score = 0
    signals = []

    # Positive keyword hits (capped so one very keyword-stuffed email
    # doesn't dominate the score)
    keyword_hits = [kw for kw in POSITIVE_KEYWORDS if kw in text]
    if keyword_hits:
        gained = min(50, 12 * len(keyword_hits))
        score += gained
        signals.append(f"Matched {len(keyword_hits)} opportunity keyword(s): {', '.join(keyword_hits[:4])}")

    # Deadline language is a strong signal — real opportunities almost
    # always mention a date to act by.
    if any(re.search(p, text) for p in DEADLINE_PATTERNS):
        score += 20
        signals.append('Mentions a deadline or due date')

    # A concrete date format nearby is an even stronger signal.
    if re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text) or \
       re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}\b', text):
        score += 10
        signals.append('Contains a specific date')

    # A link is usually present in legitimate application emails.
    if re.search(r'https?://', text):
        score += 8
        signals.append('Includes a link')

    # Trusted-looking sender domains nudge the score up.
    if any(hint in sender_lower for hint in TRUSTED_SENDER_HINTS):
        score += 10
        signals.append('Sender looks institutional')

    # Reasonable length suggests real content, not just a one-line ad.
    if len(body) > 200:
        score += 5

    # Negative signals pull the score down hard — these are strong
    # indicators of newsletters, marketing, or unrelated notifications.
    negative_hits = [kw for kw in NEGATIVE_KEYWORDS if kw in text]
    if negative_hits:
        penalty = min(45, 15 * len(negative_hits))
        score -= penalty
        signals.append(f"Looks like marketing/notification noise ({negative_hits[0]})")

    score = max(0, min(100, score))

    return {
        'score': score,
        'is_opportunity': score >= 45,
        'signals': signals,
    }
