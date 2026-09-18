from django.core.management.base import BaseCommand

from common.management_utils import command_progress
from domains.apps.foodie.services import seed_meal_defaults


class Command(BaseCommand):
    help = (
        'Set categories on each system meal from the MEAL_SLOTS map in foodie services. '
        'Safe to re-run. Run before seed_meal_default_preferences.'
    )

    def handle(self, *args, **options):
        result = seed_meal_defaults(on_progress=command_progress(self))
        if not result['unrecognised']:
            self.stdout.write(self.style.SUCCESS('\nDone.'))
