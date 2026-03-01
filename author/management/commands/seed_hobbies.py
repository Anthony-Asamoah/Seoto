from django.core.management.base import BaseCommand

from author.models import Hobby


HOBBIES = [
    "Sports: Long Tennis, Soccer and swimming.",
    "Reading random articles on Quora",
    "Learning and reading about electronics, auto_mechanics, engines, systems, etc.",
    "Photography",
    "Playing the guitar",
]


class Command(BaseCommand):
    help = 'Seeds the database with default hobbies'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding hobbies...')

        created_count = 0

        for order, description in enumerate(HOBBIES, start=1):
            _, created = Hobby.objects.get_or_create(
                description=description,
                defaults={'order': order},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {description}'))
            else:
                self.stdout.write(self.style.WARNING(f'- Already exists: {description}'))

        self.stdout.write(
            self.style.SUCCESS(f'\nSeeding complete! Created: {created_count}')
        )
