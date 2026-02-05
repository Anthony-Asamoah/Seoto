import logging

import httpx
from django.conf import settings

from seoto.model_validators import is_random_string

logger = logging.getLogger(__name__)

# Suppress httpx debug logging to prevent API keys in URLs from leaking into logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def ipqualityscore_email_checker(email: str) -> bool:
    logger.info(f'validating {email} via ipqualityscore')
    try:
        response = httpx.get(
            url=f"https://www.ipqualityscore.com/api/json/email/{settings.IP_QUALITY_SCORE_API_KEY}/{email}",
            timeout=60,
            follow_redirects=True
        )
        response.raise_for_status()
        return bool(response.json().get('valid', False))
    except Exception:
        logger.warning("External email validation service failed.")
        return True


def is_valid_email(email: str) -> bool:
    # externally validate suspicious emails
    if is_random_string(email.split('@')[0]):
        return ipqualityscore_email_checker(email)
    return True
