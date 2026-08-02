import re

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from domains.apps.blog.models import Post
from domains.apps.blog.signals import _url_to_storage_path, _BLOG_MEDIA_PREFIXES


class Command(BaseCommand):
    help = 'Delete media files in blog/images/ and blog/media/ storage not referenced by any post.'

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

        # Collect all storage paths referenced in live posts (all media tag types)
        referenced = set()
        url_pattern = re.compile(r'<(?:img|source|iframe|a)[^>]+(?:src|href)=["\']([^"\']+)["\']')
        for content in Post.objects.values_list('content', flat=True):
            if not content:
                continue
            for url in url_pattern.findall(content):
                path = _url_to_storage_path(url)
                if path:
                    referenced.add(path)

        self.stdout.write(f'Found {len(referenced)} media file(s) referenced in live posts.')

        # Scan both storage directories
        total_orphans = []
        for directory in _BLOG_MEDIA_PREFIXES:
            try:
                _, filenames = default_storage.listdir(directory)
            except FileNotFoundError:
                self.stdout.write(f'  No {directory} directory found, skipping.')
                continue

            orphans = [
                f'{directory}{name}'
                for name in filenames
                if f'{directory}{name}' not in referenced
            ]
            if orphans:
                self.stdout.write(f'  {len(orphans)} orphan(s) in {directory}')
            total_orphans.extend(orphans)

        if not total_orphans:
            self.stdout.write(self.style.SUCCESS('No orphaned media files found.'))
            return

        deleted = 0
        for path in total_orphans:
            self.stdout.write(f'  {"[dry-run] " if dry_run else ""}Deleting {path}')
            if not dry_run:
                try:
                    default_storage.delete(path)
                    deleted += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Failed to delete {path}: {e}'))

        summary = f'{len(total_orphans)} orphaned file(s) {"found" if dry_run else f"deleted ({deleted} succeeded)"}.'
        self.stdout.write(self.style.SUCCESS(summary))
