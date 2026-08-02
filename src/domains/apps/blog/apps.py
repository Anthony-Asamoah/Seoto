from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'domains.apps.blog'

    def ready(self):
        import domains.apps.blog.signals  # noqa
