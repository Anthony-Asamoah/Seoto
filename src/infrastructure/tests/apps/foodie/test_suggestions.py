from datetime import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from domains.apps.foodie.models import (
    MealTimeSlot, UserMealSchedule, meal, userPreference, DailyMealSuggestion,
)
from domains.apps.foodie.services import (
    _build_context, suggest, make_share_token, read_share_token, FANCY_MOODS, _fancy_text,
)

from .helpers import _at


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


class FancyTextTests(TestCase):
    def test_same_meal_and_slot_always_gives_the_same_mood(self):
        first = _fancy_text('Koliko', 'supper')
        for _ in range(5):
            self.assertEqual(_fancy_text('Koliko', 'supper'), first)

    def test_mood_is_one_of_the_declared_synonyms(self):
        for name in ['Koliko', 'Sushi', 'Waakye', 'Jollof', 'Banku', 'Fufu', 'Kelewele', 'Tuo Zaafi']:
            text = _fancy_text(name, 'dinner')
            self.assertTrue(
                any(f"feeling {mood}," in text for mood in FANCY_MOODS),
                f'unexpected mood in: {text}',
            )

    def test_moods_vary_across_meals(self):
        names = ['Koliko', 'Sushi', 'Waakye', 'Jollof', 'Banku', 'Fufu', 'Kelewele', 'Tuo Zaafi']
        moods = {
            next(m for m in FANCY_MOODS if f"feeling {m}," in _fancy_text(n, 'dinner'))
            for n in names
        }
        self.assertGreater(len(moods), 1)

    def test_shared_link_keeps_the_sharers_wording(self):
        MealTimeSlot.objects.create(label='supper', default_time=time(20, 0))
        m1 = meal.objects.create(name='Bread & Egg')
        fancy_meal = meal.objects.create(name='Koliko', is_fancy=True)

        original = _build_context('supper', m1, None, fancy_meal)
        restored = read_share_token(make_share_token(original))

        self.assertEqual(restored['fancy_text'], original['fancy_text'])
