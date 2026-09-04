from django.contrib.admin.apps import AdminConfig


class SeotoAdminConfig(AdminConfig):
    """Stock admin site, with the project-wide admin form tweaks installed."""

    def ready(self):
        super().ready()
        from infrastructure.utils.admin import install_select2_m2m

        install_select2_m2m()


class OTPAdminConfig(SeotoAdminConfig):
    """Swaps django.contrib.admin's default site for the TOTP-gated one."""

    default_site = 'infrastructure.core.admin.SeotoAdminSite'
