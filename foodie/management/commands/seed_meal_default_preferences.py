from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from foodie.models import meal, MealTimeSlot, userPreference

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Seed userPreference records linking every meal to every MealTimeSlot for every user. '
        'Safe to re-run (uses get_or_create). Run after seed_meal_time_slots.'
    )

    def handle(self, *args, **options):
        slots = list(MealTimeSlot.objects.exclude(label='fancy'))
        if not slots:
            self.stdout.write(self.style.WARNING(
                'No MealTimeSlot records found. Run seed_meal_time_slots first.'
            ))
            return

        meals = list(meal.objects.all())
        users = list(User.objects.all())

        if not meals:
            self.stdout.write(self.style.WARNING('No meals found in the database.'))
            return

        self.stdout.write(
            f'Seeding preferences for {len(users)} user(s), '
            f'{len(meals)} meal(s), {len(slots)} slot(s)...'
        )

        created_count = 0
        for user in users:
            for m in meals:
                for slot in slots:
                    _, created = userPreference.objects.get_or_create(
                        user=user, meal=m, slot=slot,
                        defaults={'isAvailable': True}
                    )
                    if created:
                        created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created_count} new preference record(s) created.'
        ))
