"""
reCAPTCHA v3 server-side verification utility.
"""
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def verify_recaptcha(token, action=None):
    """
    Verify a reCAPTCHA v3 token with Google's API.

    Args:
        token: The g-recaptcha-response token from the form
        action: Expected action name (optional, for additional verification)

    Returns:
        dict with keys:
            - success: bool - whether verification succeeded
            - score: float - bot score (0.0-1.0, higher is more human-like)
            - action: str - the action name from the token
            - error_codes: list - any error codes from Google
    """
    if not token:
        return {
            'success': False,
            'score': 0.0,
            'action': None,
            'error_codes': ['missing-input-response']
        }

    data = urllib.parse.urlencode({
        'secret': settings.RECAPTCHA_SECRET_KEY,
        'response': token,
    }).encode('utf-8')

    try:
        req = urllib.request.Request(settings.RECAPTCHA_VERIFY_URL, data=data)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))

        verification = {
            'success': result.get('success', False),
            'score': result.get('score', 0.0),
            'action': result.get('action'),
            'error_codes': result.get('error-codes', [])
        }

        # If action is specified, verify it matches
        if action and verification['action'] != action:
            logger.warning(
                f"reCAPTCHA action mismatch: expected '{action}', got '{verification['action']}'"
            )
            verification['success'] = False
            verification['error_codes'].append('action-mismatch')

        return verification

    except Exception as e:
        logger.error(f"reCAPTCHA verification failed: {e}")
        # Graceful degradation: if Google API fails, allow the request through
        # The honeypot will still provide protection
        return {
            'success': True,
            'score': 1.0,
            'action': action,
            'error_codes': ['network-error']
        }


def is_human(token, action=None, threshold=None):
    """
    Check if a reCAPTCHA token indicates human behavior.

    Args:
        token: The g-recaptcha-response token from the form
        action: Expected action name (optional)
        threshold: Score threshold (defaults to settings.RECAPTCHA_SCORE_THRESHOLD)

    Returns:
        tuple: (is_human: bool, score: float)
    """
    if threshold is None:
        threshold = settings.RECAPTCHA_SCORE_THRESHOLD

    result = verify_recaptcha(token, action)

    if not result['success']: return False, result['score']

    return result['score'] >= threshold, result['score']
