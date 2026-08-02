import markdown
from django.core.management.base import BaseCommand

from domains.apps.blog.models import Post


class Command(BaseCommand):
    help = 'Convert existing blog post content from Markdown to HTML for rich text editor support'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview conversions without saving to the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        posts = Post.objects.all()
        total = posts.count()

        if total == 0:
            self.stdout.write('No posts found.')
            return

        self.stdout.write(f'Found {total} post(s) to process.')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.'))

        converted = 0
        skipped = 0

        for post in posts:
            content = post.content or ''

            # Skip posts that already appear to be HTML
            stripped = content.strip()
            if stripped.startswith('<') and ('<p>' in stripped or '<h' in stripped or '<ul>' in stripped):
                self.stdout.write(self.style.WARNING(f'  SKIP  [{post.pk}] "{post.title}" — looks like HTML already'))
                skipped += 1
                continue

            html = markdown.markdown(content, extensions=['extra', 'codehilite'])

            if dry_run:
                preview = html[:120].replace('\n', ' ')
                self.stdout.write(f'  PREVIEW [{post.pk}] "{post.title}": {preview}...')
            else:
                post.content = html
                post.save(update_fields=['content'])
                self.stdout.write(self.style.SUCCESS(f'  DONE  [{post.pk}] "{post.title}"'))

            converted += 1

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Dry run complete. {converted} post(s) would be converted, {skipped} skipped.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Done. {converted} post(s) converted, {skipped} skipped.'))
