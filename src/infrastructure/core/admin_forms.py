"""Admin login forms carrying the same reCAPTCHA v3 check as the public auth forms.

Imported from `infrastructure.core.apps` inside `ready()`, never at import time:
`django.contrib.admin.forms` pulls in the auth models.
"""

from django.contrib.admin.forms import AdminAuthenticationForm

from infrastructure.core.mixins.views import enforce_recaptcha


class RecaptchaAdminLoginMixin:
    """Verify the token before the credentials, so the form can't be used to probe them."""
    recaptcha_action = 'admin_login'

    def clean(self):
        enforce_recaptcha(self.request, self.recaptcha_action)
        return super().clean()


class AdminLoginForm(RecaptchaAdminLoginMixin, AdminAuthenticationForm):
    pass
