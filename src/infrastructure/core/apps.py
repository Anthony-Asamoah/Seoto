from django.contrib.admin.apps import AdminConfig


class SeotoAdminConfig(AdminConfig):
    """Stock admin site, with the project-wide admin form tweaks installed."""

    login_form = 'infrastructure.core.admin_forms.AdminLoginForm'

    def ready(self):
        super().ready()
        from django.contrib import admin
        from django.utils.module_loading import import_string

        from infrastructure.utils.admin import install_select2_m2m

        install_select2_m2m()
        admin.site.login_form = import_string(self.login_form)


class OTPAdminConfig(SeotoAdminConfig):
    """Swaps django.contrib.admin's default site for the TOTP-gated one."""

    default_site = 'infrastructure.core.admin.SeotoAdminSite'
    login_form = 'infrastructure.core.admin.OTPAdminLoginForm'
