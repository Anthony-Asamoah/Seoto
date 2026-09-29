from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'domains.website.products'
    label = 'website_products'
    verbose_name = 'Website Products'
