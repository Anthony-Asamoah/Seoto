import ast
import logging

import httpx
from django.conf import settings

from seoto.model_validators import is_random_string


def ipqualityscore_email_checker(email: str) -> bool:
    print(f'validating {email} via ipqualityscore')
    try:
        response = httpx.get(
            url=f"https://www.ipqualityscore.com/api/json/email/{settings.IP_QUALITY_SCORE_API_KEY}/{email}",
            timeout=60,
            follow_redirects=True
        )
        response.raise_for_status()
    except httpx.HTTPError:
        logging.warning("External email validation service failed.")
        return True
    else:
        return ast.literal_eval(response.json().get('valid'))


def is_valid_email(email: str) -> bool:
    # externally validate suspicious emails
    if is_random_string(email.split('@')[0]): return ipqualityscore_email_checker(email)
    return True
