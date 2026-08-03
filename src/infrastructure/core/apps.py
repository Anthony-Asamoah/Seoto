from django.contrib.admin.apps import AdminConfig


class OTPAdminConfig(AdminConfig):
    """Swaps django.contrib.admin's default site for the TOTP-gated one."""

    default_site = 'infrastructure.core.admin.SeotoAdminSite'
