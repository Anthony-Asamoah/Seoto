from django.core.management.base import BaseCommand

from common.management_utils import command_progress
from domains.apps.foodie.services import seed_meal_default_preferences


class Command(BaseCommand):
    help = (
        'Seed userPreference records for all users from each system meal\'s categories. '
        'Safe to re-run. Run after seed_meal_time_slots and seed_meal_defaults.'
    )

    def handle(self, *args, **options):
        result = seed_meal_default_preferences(on_progress=command_progress(self))
        self.stdout.write(self.style.SUCCESS(
            f'Done. {result["created"]} new preference record(s) created.'
        ))
