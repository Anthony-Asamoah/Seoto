from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from domains.apps.foodie.models import MealTimeSlot, meal, userPreference
from domains.apps.foodie.services import (
    MEAL_TIME_SLOT_DEFAULTS,
    seed_meal_default_preferences,
    seed_meal_defaults,
    seed_meal_time_slots,
)


class SeedMealTimeSlotsTests(TestCase):
    def test_seeds_every_default_slot_and_is_idempotent(self):
        first = seed_meal_time_slots()
        self.assertEqual(first['created'], len(MEAL_TIME_SLOT_DEFAULTS))

        second = seed_meal_time_slots()
        self.assertEqual(second['created'], 0)
        self.assertEqual(MealTimeSlot.objects.count(), len(MEAL_TIME_SLOT_DEFAULTS))

    def test_progress_callback_receives_each_slot(self):
        messages = []
        seed_meal_time_slots(on_progress=lambda msg, level='info': messages.append(msg))
        self.assertEqual(len(messages), len(MEAL_TIME_SLOT_DEFAULTS))

    def test_command_wraps_the_service(self):
        out = StringIO()
        call_command('seed_meal_time_slots', stdout=out)
        self.assertIn(f'{len(MEAL_TIME_SLOT_DEFAULTS)} slot(s) created', out.getvalue())
        self.assertEqual(MealTimeSlot.objects.count(), len(MEAL_TIME_SLOT_DEFAULTS))


class SeedMealDefaultsTests(TestCase):
    def test_sets_categories_and_flags_fancy(self):
        known = meal.objects.create(name='cake', created_by=None)
        plain = meal.objects.create(name='banku', created_by=None)

        result = seed_meal_defaults()

        known.refresh_from_db()
        plain.refresh_from_db()
        self.assertEqual(result['updated'], 2)
        self.assertEqual(result['unrecognised'], [])
        # 'cake' is a snack outside SNACK_NO_FANCY, so fancy is applied automatically.
        self.assertIn('fancy', known.categories)
        self.assertTrue(known.is_fancy)
        self.assertEqual(plain.categories, ['lunch'])
        self.assertFalse(plain.is_fancy)

    def test_snack_no_fancy_meals_stay_unfancy(self):
        tea = meal.objects.create(name='tea', created_by=None)
        seed_meal_defaults()
        tea.refresh_from_db()
        self.assertNotIn('fancy', tea.categories)
        self.assertFalse(tea.is_fancy)

    def test_unrecognised_meals_are_reported_not_updated(self):
        unknown = meal.objects.create(name='not a real meal', created_by=None)

        result = seed_meal_defaults()

        unknown.refresh_from_db()
        self.assertEqual(result['unrecognised'], ['not a real meal'])
        self.assertEqual(result['updated'], 0)
        self.assertFalse(unknown.categories)

    def test_no_system_meals_is_a_noop(self):
        levels = []
        result = seed_meal_defaults(on_progress=lambda msg, level='info': levels.append(level))
        self.assertEqual(result, {'updated': 0, 'unrecognised': []})
        self.assertIn('warning', levels)


class SeedMealDefaultPreferencesTests(TestCase):
    def test_creates_a_preference_per_user_meal_and_slot(self):
        User = get_user_model()
        User.objects.create_user(username='seed_user', password='pw')
        seed_meal_time_slots()
        meal.objects.create(name='banku', created_by=None, categories=['lunch'])

        result = seed_meal_default_preferences()

        self.assertEqual(result['created'], 1)
        self.assertEqual(userPreference.objects.count(), 1)

        self.assertEqual(seed_meal_default_preferences()['created'], 0)

    def test_warns_and_stops_without_slots(self):
        levels = []
        result = seed_meal_default_preferences(
            on_progress=lambda msg, level='info': levels.append(level)
        )
        self.assertEqual(result, {'created': 0})
        self.assertIn('warning', levels)

    def test_unknown_category_labels_are_ignored(self):
        User = get_user_model()
        User.objects.create_user(username='seed_user2', password='pw')
        seed_meal_time_slots()
        meal.objects.create(name='banku', created_by=None, categories=['not_a_slot'])

        self.assertEqual(seed_meal_default_preferences()['created'], 0)
