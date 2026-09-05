from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'domains.company.hr.staff'
    label = 'company_staff'
    verbose_name = 'Company Staff'
