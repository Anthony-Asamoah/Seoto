from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from domains.apps.foodie.models import meal, MealTimeSlot, userPreference

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Seed userPreference records for all users from each system meal\'s categories. '
        'Safe to re-run. Run after seed_meal_time_slots and seed_meal_defaults.'
    )

    def handle(self, *args, **options):
        slot_map = {s.label.lower(): s for s in MealTimeSlot.objects.all()}
        if not slot_map:
            self.stdout.write(self.style.WARNING(
                'No MealTimeSlot records found. Run seed_meal_time_slots first.'
            ))
            return

        system_meals = list(meal.objects.filter(created_by=None))
        if not system_meals:
            self.stdout.write(self.style.WARNING('No system meals found in the database.'))
            return

        users = User.objects.all()
        self.stdout.write(f'Seeding preferences for {len(users)} user(s), {len(system_meals)} meal(s)...\n')

        created_count = 0
        for user in users:
            for m in system_meals:
                for label in (m.categories or []):
                    slot = slot_map.get(label.lower())
                    if not slot: continue
                    _, created = userPreference.objects.get_or_create(
                        user=user,
                        meal=m,
                        slot_id=slot.label,
                        defaults={'isAvailable': True}
                    )
                    if created:
                        created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. {created_count} new preference record(s) created.'
        ))
