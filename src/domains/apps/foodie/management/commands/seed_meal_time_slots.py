from django.core.management.base import BaseCommand

from common.management_utils import command_progress
from domains.apps.foodie.services import seed_meal_time_slots


class Command(BaseCommand):
    help = 'Seed default MealTimeSlot records (breakfast, lunch, snack, dinner)'

    def handle(self, *args, **options):
        result = seed_meal_time_slots(on_progress=command_progress(self))
        self.stdout.write(self.style.SUCCESS(f'\nDone. {result["created"]} slot(s) created.'))
