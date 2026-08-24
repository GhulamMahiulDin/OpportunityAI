"""
Minimal Gmail API client built directly on `requests` (no heavy Google SDK
needed). Handles refreshing expired access tokens and fetching/parsing
messages so the rest of the app can just deal with plain subject/body text.
"""
import base64
import re
import time
import requests
from flask import current_app

TOKEN_URL = 'https://oauth2.googleapis.com/token'
GMAIL_API_BASE = 'https://gmail.googleapis.com/gmail/v1/users/me'

# Search query used when listing messages to sync. Keeps the initial fetch
# reasonably targeted — the classifier does the real filtering afterwards.
OPPORTUNITY_KEYWORDS_QUERY = (
    '(internship OR scholarship OR fellowship OR hackathon OR competition '
    'OR "call for applications" OR "apply now" OR "application deadline" '
    'OR "research opportunity" OR traineeship) '
    '-category:promotions -category:social'
)
DEFAULT_QUERY = f'newer_than:14d {OPPORTUNITY_KEYWORDS_QUERY}'


def build_sync_query(last_synced_at=None, max_lookback_days=60):
    """
    Builds the Gmail search query for a sync run. Uses the time since the
    last successful sync (so nothing is missed if the student hasn't
    opened the app in a while) instead of always looking back a fixed
    14 days, capped at `max_lookback_days` to keep each sync bounded.
    """
    from datetime import datetime, timezone

    if not last_synced_at:
        return DEFAULT_QUERY

    if isinstance(last_synced_at, str):
        try:
            last_synced_at = datetime.fromisoformat(last_synced_at.split('.')[0])
        except ValueError:
            return DEFAULT_QUERY

    if last_synced_at.tzinfo is None:
        last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)

    days_since = (datetime.now(timezone.utc) - last_synced_at).days
    days_since = max(1, min(days_since + 1, max_lookback_days))  # +1 buffer, capped

    return f'newer_than:{days_since}d {OPPORTUNITY_KEYWORDS_QUERY}'


class GmailAuthError(Exception):
    """Raised when the stored Gmail credentials are invalid/expired and can't be refreshed."""
    pass


def refresh_access_token(refresh_token):
    """
    Exchanges a refresh token for a new access token.
    Returns dict: {'access_token':..., 'expires_at': epoch_seconds}
    """
    resp = requests.post(TOKEN_URL, data={
        'client_id': current_app.config['GOOGLE_CLIENT_ID'],
        'client_secret': current_app.config['GOOGLE_CLIENT_SECRET'],
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }, timeout=15)

    if resp.status_code != 200:
        raise GmailAuthError(f"Failed to refresh Gmail access token: {resp.text[:200]}")

    data = resp.json()
    return {
        'access_token': data['access_token'],
        'expires_at': time.time() + data.get('expires_in', 3600) - 60,  # refresh a minute early
    }


def get_valid_access_token(token_dict):
    """
    Given a stored token dict, returns a valid access_token, refreshing it
    first if it's expired. Returns (access_token, updated_token_dict_or_None).
    updated_token_dict is None when no refresh was needed.
    """
    if token_dict.get('access_token') and token_dict.get('expires_at', 0) > time.time():
        return token_dict['access_token'], None

    if not token_dict.get('refresh_token'):
        raise GmailAuthError('No refresh token on file — the account needs to be reconnected.')

    refreshed = refresh_access_token(token_dict['refresh_token'])
    updated = dict(token_dict)
    updated['access_token'] = refreshed['access_token']
    updated['expires_at'] = refreshed['expires_at']
    return updated['access_token'], updated


def list_recent_messages(access_token, query=None, max_results=25):
    """
    Returns a list of {'id': ..., 'threadId': ...} for messages matching the query.
    """
    resp = requests.get(
        f'{GMAIL_API_BASE}/messages',
        headers={'Authorization': f'Bearer {access_token}'},
        params={'q': query or DEFAULT_QUERY, 'maxResults': max_results},
        timeout=15
    )
    if resp.status_code == 401:
        raise GmailAuthError('Gmail access token was rejected (401). Try reconnecting Gmail in Settings.')
    if resp.status_code == 403:
        raise GmailAuthError(
            'Gmail API returned 403 Forbidden. This almost always means the Gmail API '
            'is not enabled in your Google Cloud project. Go to console.cloud.google.com '
            '→ APIs & Services → Library → search "Gmail API" → Enable, then try syncing again.'
        )
    resp.raise_for_status()
    return resp.json().get('messages', [])


def get_message(access_token, message_id):
    """Fetches a single message in full format."""
    resp = requests.get(
        f'{GMAIL_API_BASE}/messages/{message_id}',
        headers={'Authorization': f'Bearer {access_token}'},
        params={'format': 'full'},
        timeout=15
    )
    if resp.status_code == 401:
        raise GmailAuthError('Gmail access token was rejected (401). Try reconnecting Gmail in Settings.')
    if resp.status_code == 403:
        raise GmailAuthError(
            'Gmail API returned 403 Forbidden. Make sure the Gmail API is enabled for '
            'your Google Cloud project (APIs & Services → Library → Gmail API → Enable).'
        )
    resp.raise_for_status()
    return resp.json()


def _b64url_decode(data):
    padded = data + '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def _strip_html(html_text):
    """Very small HTML->text fallback (no external deps)."""
    text = re.sub(r'(?is)<(script|style).*?>.*?</\1>', ' ', html_text)
    text = re.sub(r'(?i)<br\s*/?>', '\n', text)
    text = re.sub(r'(?i)</p>', '\n', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()


def _walk_parts(payload):
    """Yields every MIME part (including nested multiparts) of a message payload."""
    if not payload:
        return
    yield payload
    for part in payload.get('parts', []) or []:
        yield from _walk_parts(part)


def parse_message(message_json):
    """
    Extracts a clean, plain-text version of a Gmail message plus its headers.
    Returns: {'subject', 'sender', 'received_at', 'body_text'}
    """
    headers = {h['name'].lower(): h['value'] for h in message_json.get('payload', {}).get('headers', [])}
    subject = headers.get('subject', '(no subject)')
    sender = headers.get('from', '')
    received_at = headers.get('date', '')

    plain_text = ''
    html_text = ''

    for part in _walk_parts(message_json.get('payload', {})):
        mime_type = part.get('mimeType', '')
        body_data = part.get('body', {}).get('data')
        if not body_data:
            continue
        try:
            decoded = _b64url_decode(body_data).decode('utf-8', errors='ignore')
        except Exception:
            continue
        if mime_type == 'text/plain' and not plain_text:
            plain_text = decoded
        elif mime_type == 'text/html' and not html_text:
            html_text = decoded

    body_text = plain_text.strip() or _strip_html(html_text)
    # Keep it bounded — long marketing emails don't need 50KB of footer text.
    body_text = body_text[:6000]

    return {
        'subject': subject,
        'sender': sender,
        'received_at': received_at,
        'body_text': body_text,
    }
