from django.core.management.base import BaseCommand
from foodie.models import MealTimeSlot

DEFAULTS = [
    ('breakfast', '08:00'),
    ('lunch',     '12:00'),
    ('snack',     '15:00'),
    ('dinner',    '18:00'),
    ('supper',    '20:00'),
    ('fancy',     '00:00'),  # Pseudo-slot — not time-based; used for fancy meal preferences
]


class Command(BaseCommand):
    help = 'Seed default MealTimeSlot records (breakfast, lunch, snack, dinner)'

    def handle(self, *args, **options):
        created_count = 0
        for label, default_time in DEFAULTS:
            slot, created = MealTimeSlot.objects.get_or_create(
                label=label,
                defaults={'default_time': default_time}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {label} @ {default_time}'))
            else:
                self.stdout.write(f'  Already exists: {label} @ {slot.default_time}')

        self.stdout.write(self.style.SUCCESS(f'\nDone. {created_count} slot(s) created.'))
