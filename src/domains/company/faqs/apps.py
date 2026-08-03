from django.apps import AppConfig


class FAQsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'domains.company.faqs'
    label = 'company_faqs'
    verbose_name = 'Company FAQs'
