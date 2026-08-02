from django.core.management.base import BaseCommand

from domains.apps.foodie.models import meal


class Command(BaseCommand):
    help = 'Generate missing thumbnails for existing meal images'

    def handle(self, *args, **kwargs):
        qs = meal.objects.filter(main_img__isnull=False).exclude(main_img='')
        count, skipped = 0, 0
        for m in qs:
            if m.main_img_thumbnail:
                skipped += 1
                continue
            m._generate_thumbnail()
            count += 1
            self.stdout.write(f'  Generated thumbnail for: {m.name}')
        self.stdout.write(self.style.SUCCESS(
            f'Done. Generated: {count}, Already had thumbnail: {skipped}'
        ))
