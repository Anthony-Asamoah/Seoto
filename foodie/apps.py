from django.apps import AppConfig


class FoodieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'foodie'

    def ready(self):
        # Import signals on app ready
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Do not break startup if signals import fails in certain contexts
            pass
