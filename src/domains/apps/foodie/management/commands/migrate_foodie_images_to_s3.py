from django.core.management.base import BaseCommand

from common.management_utils import command_progress
from domains.apps.foodie.services import migrate_meal_images_to_s3


class Command(BaseCommand):
    help = 'One-time migration of local foodie images to S3'

    def handle(self, *args, **kwargs):
        result = migrate_meal_images_to_s3(on_progress=command_progress(self))
        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Uploaded: {result["uploaded"]}, '
            f'Skipped: {result["skipped"]}, Missing: {result["missing"]}'
        ))
