from django.contrib.admin.apps import AdminConfig


class SeotoAdminConfig(AdminConfig):
    """Unfold admin site, with the reCAPTCHA-checked login form installed."""

    default_site = 'unfold.sites.UnfoldAdminSite'
    login_form = 'common.admin_forms.AdminLoginForm'

    def ready(self):
        super().ready()
        from django.contrib import admin
        from django.utils.module_loading import import_string

        admin.site.login_form = import_string(self.login_form)


class OTPAdminConfig(SeotoAdminConfig):
    """Swaps django.contrib.admin's default site for the TOTP-gated one."""

    default_site = 'common.admin.SeotoAdminSite'
    login_form = 'common.admin.OTPAdminLoginForm'
