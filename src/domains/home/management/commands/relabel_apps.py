from django.core.management.base import BaseCommand

from common.management_utils import command_progress
from domains.home.services import relabel_apps


class Command(BaseCommand):
    help = 'Rename tables, migration history and content types for apps whose label changed. Run before migrate.'

    def handle(self, *args, **options):
        relabel_apps(on_progress=command_progress(self))
