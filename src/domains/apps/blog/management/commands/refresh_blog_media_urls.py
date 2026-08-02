"""
Management command: refresh_blog_media_urls

Replaces expired S3 pre-signed URLs embedded in Post.content with the
proxy URL (/blog/media/serve/<path>/) so media is always accessible.

Usage:
    python manage.py refresh_blog_media_urls            # live run
    python manage.py refresh_blog_media_urls --dry-run  # preview only
"""
import re

from django.core.management.base import BaseCommand
from django.urls import reverse

from domains.apps.blog.models import Post
from domains.apps.blog.signals import _url_to_storage_path

# Matches src/href values that look like S3 pre-signed URLs (contain X-Amz- params)
# or any URL containing known blog storage prefixes — catches both fresh and expired sigs.
_URL_ATTRS = re.compile(
    r'((?:src|href)=["\'])([^"\']+?)((?:blog/(?:images|media)/)[^"\']*?)([^"\']*["\'])',
    re.IGNORECASE,
)

# Simpler: find all src/href values anywhere in the content
_SRC_HREF = re.compile(r'(?:src|href)=["\']([^"\']+)["\']', re.IGNORECASE)


class Command(BaseCommand):
    help = 'Replace S3 pre-signed media URLs in blog post content with proxy URLs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print planned replacements without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        posts = Post.objects.all()
        total_replaced = 0
        posts_changed = 0

        for post in posts:
            if not post.content:
                continue

            new_content = post.content
            replacements = 0

            for url in set(_SRC_HREF.findall(post.content)):
                # Skip if already a proxy URL
                if '/blog/media/serve/' in url or url.startswith('/media/'):
                    continue

                storage_path = _url_to_storage_path(url)
                if not storage_path:
                    continue

                proxy_url = reverse('blog-serve-media', kwargs={'path': storage_path})
                new_content = new_content.replace(url, proxy_url)
                replacements += 1

                if dry_run:
                    self.stdout.write(
                        f'  [Post {post.pk}] {url[:80]}…\n'
                        f'         → {proxy_url}'
                    )

            if replacements:
                total_replaced += replacements
                posts_changed += 1
                if not dry_run:
                    post.content = new_content
                    post.save(update_fields=['content'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Post {post.pk} ({post.title!r}): {replacements} URL(s) updated.'
                        )
                    )

        summary = (
            f'\n{"[DRY RUN] " if dry_run else ""}'
            f'{total_replaced} URL(s) across {posts_changed} post(s) '
            f'{"would be" if dry_run else "were"} updated.'
        )
        self.stdout.write(self.style.SUCCESS(summary))
