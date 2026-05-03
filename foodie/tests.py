from datetime import datetime, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from foodie.models import MealTimeSlot, UserMealSchedule
from foodie.services import _current_mealtime


def _at(hour, minute=0):
    """Build a datetime for today at the given wall-clock time."""
    return datetime(2026, 5, 3, hour, minute)


class CurrentMealtimeAuthenticatedTests(TestCase):
    """User has lunch=13:00, dinner=16:00, breakfast=08:00."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username='tester', password='pw')

        breakfast = MealTimeSlot.objects.create(label='breakfast', default_time=time(8, 0))
        lunch = MealTimeSlot.objects.create(label='lunch', default_time=time(13, 0))
        dinner = MealTimeSlot.objects.create(label='dinner', default_time=time(16, 0))
        MealTimeSlot.objects.create(label='fancy', default_time=time(0, 0))

        UserMealSchedule.objects.create(user=cls.user, slot=breakfast, time=time(8, 0))
        UserMealSchedule.objects.create(user=cls.user, slot=lunch, time=time(13, 0))
        UserMealSchedule.objects.create(user=cls.user, slot=dinner, time=time(16, 0))

    def _assert_at(self, hour, minute, expected):
        with patch('foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(hour, minute)
            self.assertEqual(_current_mealtime(self.user), expected)

    def test_exactly_at_lunch_start(self):
        self._assert_at(13, 0, 'lunch')

    def test_mid_lunch_window(self):
        self._assert_at(14, 30, 'lunch')

    def test_one_minute_before_dinner(self):
        self._assert_at(15, 59, 'lunch')

    def test_exactly_at_dinner_start(self):
        self._assert_at(16, 0, 'dinner')

    def test_well_after_dinner_still_dinner(self):
        self._assert_at(20, 0, 'dinner')

    def test_late_night_wraps_to_last_slot(self):
        self._assert_at(23, 30, 'dinner')

    def test_before_first_slot_wraps_to_last(self):
        self._assert_at(2, 0, 'dinner')

    def test_at_breakfast(self):
        self._assert_at(8, 0, 'breakfast')

    def test_between_breakfast_and_lunch(self):
        self._assert_at(11, 0, 'breakfast')

    def test_fancy_slot_is_excluded(self):
        # Add a fancy schedule entry at noon — should not be selected even though now=12:30 > 12:00.
        fancy_slot = MealTimeSlot.objects.get(label='fancy')
        UserMealSchedule.objects.create(user=self.user, slot=fancy_slot, time=time(12, 0))
        with patch('foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(12, 30)
            self.assertEqual(_current_mealtime(self.user), 'breakfast')


class CurrentMealtimeSingleSlotTests(TestCase):
    """User with a single slot — wrap-around must always return that slot."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username='solo', password='pw')
        lunch = MealTimeSlot.objects.create(label='lunch', default_time=time(13, 0))
        UserMealSchedule.objects.create(user=cls.user, slot=lunch, time=time(13, 0))

    def test_before_only_slot(self):
        with patch('foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(6, 0)
            self.assertEqual(_current_mealtime(self.user), 'lunch')

    def test_after_only_slot(self):
        with patch('foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(22, 0)
            self.assertEqual(_current_mealtime(self.user), 'lunch')


class CurrentMealtimeFallbackTests(TestCase):
    """No schedule / anonymous → hour-based fallback."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user_no_schedule = User.objects.create_user(username='blank', password='pw')

    def _assert_anon_at(self, hour, expected):
        with patch('foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(hour)
            self.assertEqual(_current_mealtime(AnonymousUser()), expected)

    def test_fallback_breakfast(self):
        self._assert_anon_at(7, 'breakfast')

    def test_fallback_lunch(self):
        self._assert_anon_at(12, 'lunch')

    def test_fallback_dinner(self):
        self._assert_anon_at(17, 'dinner')

    def test_fallback_snack(self):
        self._assert_anon_at(20, 'snack')

    def test_fallback_late_night_returns_none(self):
        self._assert_anon_at(2, None)

    def test_authenticated_no_schedule_uses_fallback(self):
        with patch('foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(12)
            self.assertEqual(_current_mealtime(self.user_no_schedule), 'lunch')

    def test_authenticated_only_fancy_uses_fallback(self):
        fancy = MealTimeSlot.objects.create(label='fancy', default_time=time(0, 0))
        UserMealSchedule.objects.create(user=self.user_no_schedule, slot=fancy, time=time(12, 0))
        with patch('foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(17)
            self.assertEqual(_current_mealtime(self.user_no_schedule), 'dinner')
