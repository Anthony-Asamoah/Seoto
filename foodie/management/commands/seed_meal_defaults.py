from django.core.management.base import BaseCommand

from foodie.models import meal

# Meals with snack that should NOT get fancy auto-applied
SNACK_NO_FANCY = {'tea', 'indomie'}

# Base slots per meal (snack → fancy is applied automatically below)
MEAL_SLOTS = {
    'burgers':                    ['lunch', 'dinner'],
    'assorted fried rice':        ['lunch', 'dinner'],
    'banku':                      ['lunch'],
    'bread & egg':                ['breakfast'],
    'cake':                       ['snack'],
    'fried rice':                 ['lunch', 'dinner'],
    'fufu':                       ['lunch'],
    'fula':                       ['breakfast', 'snack'],
    'g)b3':                       ['breakfast', 'lunch'],
    'ice cream':                  ['snack'],
    'indomie':                    ['breakfast', 'lunch'],
    'jollof':                     ['lunch', 'dinner'],
    'kenkey':                     ['breakfast', 'lunch', 'dinner'],
    'koliko':                     ['lunch', 'snack'],
    'pastries':                   ['breakfast', 'snack'],
    'pie':                        ['breakfast', 'lunch', 'snack'],
    'pizza':                      ['lunch', 'dinner'],
    'pork and fries':             ['lunch', 'dinner'],
    'spring rolls':               ['breakfast', 'lunch', 'snack'],
    'tea':                        ['breakfast', 'snack'],
    'waakye & jollof combo':      ['breakfast', 'lunch', 'dinner'],
    'waakye':                     ['breakfast', 'lunch'],
    'assorted spaghetti (sauce)': ['lunch', 'dinner'],
    'loaded fries':               ['lunch', 'snack', 'supper'],
    'boba smoothie':              ['breakfast', 'snack'],
    'sharwama':                   ['lunch', 'dinner'],
    'lasagna':                    ['lunch', 'dinner', 'supper'],
}


def _resolve_slots(name: str) -> list[str]:
    key = name.lower().strip()
    slots = MEAL_SLOTS.get(key, [])
    if 'snack' in slots and 'fancy' not in slots and key not in SNACK_NO_FANCY:
        slots = slots + ['fancy']
    return slots


class Command(BaseCommand):
    help = (
        'Set categories on each system meal from the hardcoded MEAL_SLOTS map. '
        'Safe to re-run. Run before seed_meal_default_preferences.'
    )

    def handle(self, *args, **options):
        system_meals = list(meal.objects.filter(created_by=None))

        if not system_meals:
            self.stdout.write(self.style.WARNING('No system meals found in the database.'))
            return

        self.stdout.write(f'Setting defaults for {len(system_meals)} system meal(s)...\n')

        unrecognised = []
        for m in system_meals:
            slots = _resolve_slots(m.name)
            if not slots:
                unrecognised.append(m.name)
                continue
            is_fancy = 'fancy' in slots
            meal.objects.filter(pk=m.pk).update(categories=slots, is_fancy=is_fancy)
            self.stdout.write(f'  {m.name}: {slots}{"  [fancy]" if is_fancy else ""}')

        if unrecognised:
            self.stdout.write(self.style.WARNING(
                f'\nUnrecognised meals (no slots assigned): {unrecognised}'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\nDone.'))
