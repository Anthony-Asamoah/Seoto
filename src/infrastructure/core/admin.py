"""Admin site wiring: a TOTP second factor on top of the stock admin login.

Imported lazily by Django (see `infrastructure.core.apps.OTPAdminConfig`), because
django_otp pulls in auth models that aren't loadable while INSTALLED_APPS is being read.
"""

from django_otp.admin import OTPAdminSite


class SeotoAdminSite(OTPAdminSite):
    """Admin site that treats users without a verified OTP device as non-staff."""

    # Keep the stock instance name, otherwise every {% url 'admin:...' %} breaks.
    name = 'admin'

    # django-otp defaults to its own bare template; use ours so jazzmin still skins it.
    login_template = 'admin/login.html'

    def __init__(self, name='admin'):
        super().__init__(name)
