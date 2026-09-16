"""
Custom context processors for Seoto.
"""
from django.conf import settings


def recaptcha_site_key(request):
    """Make the reCAPTCHA site key available in all templates."""
    return {'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY}
