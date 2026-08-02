from django.core.management.base import BaseCommand

from domains.apps.blog.models import PostTags, PostReadGroup
from domains.apps.blog.utils import pluralize_label, singularize_label


class Command(BaseCommand):
    help = 'Sanitize existing tags to singular lowercase and read groups to plural lowercase, merging duplicates.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.\n'))

        self._sanitize_tags(dry_run)
        self._sanitize_groups(dry_run)

    def _sanitize_tags(self, dry_run):
        self.stdout.write('--- Tags ---')
        tags = PostTags.objects.all().order_by('label')
        changed = skipped = merged = 0

        for tag in tags:
            clean = singularize_label(tag.label)
            if clean == tag.label:
                skipped += 1
                continue

            # Check if a tag with the clean label already exists
            existing = PostTags.objects.filter(label=clean).exclude(pk=tag.pk).first()
            if existing:
                # Merge: reassign all posts using this tag to the existing clean one
                for post in tag.post_set.all():
                    post.tags.add(existing)
                    post.tags.remove(tag)
                self.stdout.write(
                    f'  Merged tag "{tag.label}" → "{clean}" (duplicate of pk={existing.pk})'
                )
                if not dry_run:
                    tag.delete()
                merged += 1
            else:
                self.stdout.write(f'  Renamed tag "{tag.label}" → "{clean}"')
                if not dry_run:
                    tag.label = clean
                    tag.save(update_fields=['label'])
                changed += 1

        self.stdout.write(self.style.SUCCESS(
            f'Tags: {changed} renamed, {merged} merged, {skipped} already clean.\n'
        ))

    def _sanitize_groups(self, dry_run):
        self.stdout.write('--- Read Groups ---')
        groups = PostReadGroup.objects.all().order_by('label')
        changed = skipped = merged = 0

        for group in groups:
            clean = pluralize_label(group.label)
            if clean == group.label:
                skipped += 1
                continue

            # Check if a group with the same author and clean label already exists
            existing = PostReadGroup.objects.filter(
                author=group.author, label=clean
            ).exclude(pk=group.pk).first()

            if existing:
                # Merge: move users and post references to the existing clean group
                for user in group.users.all():
                    existing.users.add(user)
                for post in group.allowed_posts.all():
                    post.allowed_groups.add(existing)
                    post.allowed_groups.remove(group)
                self.stdout.write(
                    f'  Merged group "{group.label}" (owner: {group.author}) '
                    f'→ "{clean}" (duplicate of pk={existing.pk})'
                )
                if not dry_run:
                    group.delete()
                merged += 1
            else:
                self.stdout.write(
                    f'  Renamed group "{group.label}" (owner: {group.author}) → "{clean}"'
                )
                if not dry_run:
                    group.label = clean
                    group.save(update_fields=['label'])
                changed += 1

        self.stdout.write(self.style.SUCCESS(
            f'Groups: {changed} renamed, {merged} merged, {skipped} already clean.'
        ))
