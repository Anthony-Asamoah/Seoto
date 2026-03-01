from django.core.management.base import BaseCommand

from accounts.models import user_profile


class Command(BaseCommand):
    help = 'Generate missing thumbnails for existing user profile pictures'

    def handle(self, *args, **kwargs):
        qs = user_profile.objects.filter(picture__isnull=False).exclude(picture='')
        count, skipped = 0, 0
        for p in qs:
            if p.picture_thumbnail:
                skipped += 1
                continue
            p._generate_thumbnail()
            count += 1
            self.stdout.write(f'  Generated thumbnail for: {p.user.username}')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Generated: {count}, Already had thumbnail: {skipped}'
        ))
