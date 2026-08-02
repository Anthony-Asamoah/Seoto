from datetime import datetime, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from domains.apps.foodie.models import MealTimeSlot, UserMealSchedule, meal, userPreference, DailyMealSuggestion
from domains.apps.foodie.services import _current_mealtime, suggest, send_due_meal_notifications


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
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
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
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
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
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(6, 0)
            self.assertEqual(_current_mealtime(self.user), 'lunch')

    def test_after_only_slot(self):
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(22, 0)
            self.assertEqual(_current_mealtime(self.user), 'lunch')


class CurrentMealtimeFallbackTests(TestCase):
    """No schedule / anonymous → hour-based fallback."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user_no_schedule = User.objects.create_user(username='blank', password='pw')

    def _assert_anon_at(self, hour, expected):
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
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
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(12)
            self.assertEqual(_current_mealtime(self.user_no_schedule), 'lunch')

    def test_authenticated_only_fancy_uses_fallback(self):
        fancy = MealTimeSlot.objects.create(label='fancy', default_time=time(0, 0))
        UserMealSchedule.objects.create(user=self.user_no_schedule, slot=fancy, time=time(12, 0))
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(17)
            self.assertEqual(_current_mealtime(self.user_no_schedule), 'dinner')


class SuggestStabilityTests(TestCase):
    """suggest() must be stable per (user, date, slot) and avoid intra-day repeats."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username='eater', password='pw')

        cls.lunch = MealTimeSlot.objects.create(label='lunch', default_time=time(13, 0))
        cls.dinner = MealTimeSlot.objects.create(label='dinner', default_time=time(18, 0))
        cls.fancy_slot = MealTimeSlot.objects.create(label='fancy', default_time=time(0, 0))

        UserMealSchedule.objects.create(user=cls.user, slot=cls.lunch, time=time(13, 0))
        UserMealSchedule.objects.create(user=cls.user, slot=cls.dinner, time=time(18, 0))

        # 6 lunch meals, 6 dinner meals, 2 fancy meals
        cls.lunch_meals = [meal.objects.create(name=f'Lunch{i}') for i in range(6)]
        cls.dinner_meals = [meal.objects.create(name=f'Dinner{i}') for i in range(6)]
        cls.fancy_meals = [meal.objects.create(name=f'Fancy{i}', is_fancy=True) for i in range(2)]

        for m in cls.lunch_meals:
            userPreference.objects.create(user=cls.user, meal=m, slot=cls.lunch, isAvailable=True)
        for m in cls.dinner_meals:
            userPreference.objects.create(user=cls.user, meal=m, slot=cls.dinner, isAvailable=True)
        for m in cls.fancy_meals:
            userPreference.objects.create(user=cls.user, meal=m, slot=cls.fancy_slot, isAvailable=True)

    def _suggest_at(self, hour, **kwargs):
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(hour)
            return suggest(self.user, **kwargs)

    def test_repeated_calls_same_slot_return_same_meals(self):
        first = self._suggest_at(13)
        second = self._suggest_at(13)
        third = self._suggest_at(15)  # still lunch window
        self.assertEqual(first['option_1']['id'], second['option_1']['id'])
        self.assertEqual(first['option_2']['id'], second['option_2']['id'])
        self.assertEqual(first['option_1']['id'], third['option_1']['id'])
        self.assertEqual(first['option_2']['id'], third['option_2']['id'])

    def test_within_suggestion_options_are_distinct(self):
        ctx = self._suggest_at(13)
        ids = {ctx['option_1']['id'], ctx['option_2']['id']}
        self.assertEqual(len(ids), 2)
        if 'fancy' in ctx:
            self.assertNotIn(ctx['fancy']['id'], ids)

    def test_no_meal_repeats_across_slots_in_same_day(self):
        lunch_ctx = self._suggest_at(13)
        dinner_ctx = self._suggest_at(18)
        lunch_ids = {lunch_ctx['option_1']['id'], lunch_ctx['option_2']['id']}
        dinner_ids = {dinner_ctx['option_1']['id'], dinner_ctx['option_2']['id']}
        self.assertEqual(lunch_ids & dinner_ids, set())
        # Fancy chosen at lunch should not also be option for dinner (and vice versa).
        if 'fancy' in lunch_ctx and 'fancy' in dinner_ctx:
            self.assertNotEqual(lunch_ctx['fancy']['id'], dinner_ctx['fancy']['id'])

    def test_persisted_to_daily_suggestion_table(self):
        self._suggest_at(13)
        self.assertEqual(
            DailyMealSuggestion.objects.filter(user=self.user, slot=self.lunch).count(), 1
        )

    def test_single_meal_pool_omits_option_2(self):
        User = get_user_model()
        solo = User.objects.create_user(username='solo_eater', password='pw')
        UserMealSchedule.objects.update_or_create(
            user=solo, slot=self.lunch, defaults={'time': time(13, 0)}
        )
        # Remove any auto-seeded prefs from the signal so the pool is exactly one meal.
        userPreference.objects.filter(user=solo).delete()
        only = meal.objects.create(name='OnlyOne')
        userPreference.objects.create(user=solo, meal=only, slot=self.lunch, isAvailable=True)

        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(13)
            ctx = suggest(solo)

        self.assertEqual(ctx['option_1']['id'], only.id)
        self.assertIsNone(ctx['option_2'])

    def test_pool_exhaustion_falls_back_to_repeats(self):
        # User with only 2 lunch meals — covering option_1+option_2 in one slot exhausts the pool.
        User = get_user_model()
        u = User.objects.create_user(username='small_pool', password='pw')
        UserMealSchedule.objects.update_or_create(user=u, slot=self.lunch, defaults={'time': time(13, 0)})
        UserMealSchedule.objects.update_or_create(user=u, slot=self.dinner, defaults={'time': time(18, 0)})
        userPreference.objects.filter(user=u).delete()
        m1 = meal.objects.create(name='SmallA')
        m2 = meal.objects.create(name='SmallB')
        for m in (m1, m2):
            userPreference.objects.create(user=u, meal=m, slot=self.lunch, isAvailable=True)
            userPreference.objects.create(user=u, meal=m, slot=self.dinner, isAvailable=True)

        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(13)
            lunch_ctx = suggest(u)
            mock_dt.now.return_value = _at(18)
            dinner_ctx = suggest(u)

        # Dinner falls back since pool is fully used by lunch — but options must still be distinct.
        self.assertNotEqual(dinner_ctx['option_1']['id'], dinner_ctx['option_2']['id'])
        self.assertIsNotNone(dinner_ctx['option_1'])
        self.assertIsNotNone(dinner_ctx['option_2'])


class SuggestAnonymousSessionTests(TestCase):
    """Anonymous flow caches suggestions in the session for stability + uniqueness."""

    @classmethod
    def setUpTestData(cls):
        cls.lunch = MealTimeSlot.objects.create(label='lunch', default_time=time(13, 0))
        cls.dinner = MealTimeSlot.objects.create(label='dinner', default_time=time(18, 0))

        cls.meals = []
        for label in ('lunch', 'dinner'):
            for i in range(4):
                m = meal.objects.create(
                    name=f'{label.capitalize()}A{i}', is_public=True, categories=[label]
                )
                cls.meals.append(m)

    def _make_request(self):
        class FakeSession(dict):
            modified = False
        class Req:
            pass
        r = Req()
        r.user = AnonymousUser()
        r.session = FakeSession()
        return r

    def test_anonymous_session_caches_within_slot(self):
        req = self._make_request()
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(12)  # fallback → lunch
            first = suggest(request=req)
            second = suggest(request=req)
        self.assertEqual(first['option_1']['id'], second['option_1']['id'])
        self.assertEqual(first['option_2']['id'], second['option_2']['id'])

    def test_anonymous_no_repeats_across_slots(self):
        req = self._make_request()
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(12)
            lunch_ctx = suggest(request=req)
            mock_dt.now.return_value = _at(17)  # fallback → dinner
            dinner_ctx = suggest(request=req)

        lunch_ids = {lunch_ctx['option_1']['id'], lunch_ctx['option_2']['id']}
        dinner_ids = {dinner_ctx['option_1']['id'], dinner_ctx['option_2']['id']}
        self.assertEqual(lunch_ids & dinner_ids, set())


class SendDueMealNotificationsTests(TestCase):
    """send_due_meal_notifications pushes to users whose schedule is due this hour."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username='notif_user', password='pw')

        cls.lunch = MealTimeSlot.objects.create(label='lunch', default_time=time(13, 0))
        MealTimeSlot.objects.create(label='fancy', default_time=time(0, 0))

        UserMealSchedule.objects.update_or_create(
            user=cls.user, slot=cls.lunch, defaults={'time': time(13, 0)}
        )

        # Clear any signal-seeded prefs, then give the user two lunch meals.
        userPreference.objects.filter(user=cls.user).delete()
        for name in ('NotifA', 'NotifB'):
            m = meal.objects.create(name=name)
            userPreference.objects.create(user=cls.user, meal=m, slot=cls.lunch, isAvailable=True)

    def _add_subscription(self, user):
        from domains.pwa.models import PushSubscription
        PushSubscription.objects.create(
            user=user,
            endpoint=f'https://example.com/push/{user.id}',
            p256dh='p256dh-key',
            auth='auth-key',
            is_active=True,
        )

    def test_sends_to_subscribed_user(self):
        self._add_subscription(self.user)
        with patch('domains.apps.foodie.services.datetime') as mock_dt, \
                patch('domains.pwa.services.send_push_notification', return_value=1) as mock_push:
            mock_dt.now.return_value = _at(13)
            result = send_due_meal_notifications()

        mock_push.assert_called_once()
        self.assertEqual(result, {'sent': 1, 'skipped': 0})

    def test_skips_user_without_active_subscription(self):
        with patch('domains.apps.foodie.services.datetime') as mock_dt, \
                patch('domains.pwa.services.send_push_notification') as mock_push:
            mock_dt.now.return_value = _at(13)
            result = send_due_meal_notifications()

        mock_push.assert_not_called()
        self.assertEqual(result, {'sent': 0, 'skipped': 1})

    def test_no_schedules_for_hour(self):
        with patch('domains.apps.foodie.services.datetime') as mock_dt, \
                patch('domains.pwa.services.send_push_notification') as mock_push:
            mock_dt.now.return_value = _at(3)  # no schedule at 03:xx
            result = send_due_meal_notifications()

        mock_push.assert_not_called()
        self.assertEqual(result, {'sent': 0, 'skipped': 0})
