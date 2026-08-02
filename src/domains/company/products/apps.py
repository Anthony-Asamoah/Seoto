from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'domains.company.products'
    label = 'company_products'
    verbose_name = 'Company Products'
