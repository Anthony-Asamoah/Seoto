import re

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from blog.models import Post
from blog.signals import _url_to_storage_path


class Command(BaseCommand):
    help = 'Delete images in blog/images/ storage that are not referenced by any post.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview orphaned files without deleting them.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no files will be deleted.\n'))

        # Collect all storage paths referenced in live posts
        referenced = set()
        for content in Post.objects.values_list('content', flat=True):
            if not content:
                continue
            for url in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content):
                path = _url_to_storage_path(url)
                if path:
                    referenced.add(path)

        self.stdout.write(f'Found {len(referenced)} image(s) referenced in live posts.')

        # List all files in the blog/images/ directory
        try:
            _, filenames = default_storage.listdir('blog/images/')
        except FileNotFoundError:
            self.stdout.write('No blog/images/ directory found in storage. Nothing to clean.')
            return

        orphans = [
            f'blog/images/{name}'
            for name in filenames
            if f'blog/images/{name}' not in referenced
        ]

        if not orphans:
            self.stdout.write(self.style.SUCCESS('No orphaned images found.'))
            return

        deleted = 0
        for path in orphans:
            self.stdout.write(f'  {"[dry-run] " if dry_run else ""}Deleting {path}')
            if not dry_run:
                try:
                    default_storage.delete(path)
                    deleted += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Failed to delete {path}: {e}'))

        summary = f'{len(orphans)} orphaned file(s) {"found" if dry_run else f"deleted ({deleted} succeeded)"}.'
        self.stdout.write(self.style.SUCCESS(summary))
