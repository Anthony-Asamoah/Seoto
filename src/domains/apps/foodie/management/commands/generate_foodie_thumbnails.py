from django.core.management.base import BaseCommand

from common.management_utils import command_progress
from domains.apps.foodie.services import generate_meal_thumbnails


class Command(BaseCommand):
    help = 'Generate missing thumbnails for existing meal images'

    def handle(self, *args, **kwargs):
        result = generate_meal_thumbnails(on_progress=command_progress(self))
        self.stdout.write(self.style.SUCCESS(
            f'Done. Generated: {result["generated"]}, Already had thumbnail: {result["skipped"]}'
        ))
