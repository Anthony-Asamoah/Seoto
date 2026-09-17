import time as time_module
from datetime import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from domains.apps.foodie.models import MealTimeSlot, UserMealSchedule, meal, userPreference
from domains.apps.foodie.services import (
    _build_context, ShareTokenError, ShareTokenExpired, make_share_token, read_share_token,
)

from .helpers import _at


class ShareTokenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username='sharer', password='pw')
        cls.lunch = MealTimeSlot.objects.create(label='lunch', default_time=time(13, 0))
        cls.m1 = meal.objects.create(name='Jollof')
        cls.m2 = meal.objects.create(name='Waakye')
        cls.fancy_meal = meal.objects.create(name='Sushi', is_fancy=True)
        cls.private_meal = meal.objects.create(name='Secret Stew', created_by=cls.user, is_public=False)

    def _context(self):
        return _build_context('lunch', self.m1, self.m2, self.fancy_meal)

    def test_round_trip_preserves_meals(self):
        token = make_share_token(self._context())
        restored = read_share_token(token)

        self.assertEqual(restored['mealtime'], 'lunch')
        self.assertEqual(restored['option_1']['id'], self.m1.id)
        self.assertEqual(restored['option_2']['id'], self.m2.id)
        self.assertEqual(restored['fancy']['id'], self.fancy_meal.id)
        self.assertEqual(restored['suggestion_text'], self._context()['suggestion_text'])

    def test_private_meal_is_shareable(self):
        token = make_share_token(_build_context('lunch', self.private_meal, None, None))
        restored = read_share_token(token)

        self.assertEqual(restored['option_1']['id'], self.private_meal.id)

    def test_token_without_option_2(self):
        token = make_share_token(_build_context('lunch', self.m1, None, None))
        restored = read_share_token(token)

        self.assertEqual(restored['option_1']['id'], self.m1.id)
        self.assertIsNone(restored['option_2'])

    def test_empty_context_yields_no_token(self):
        self.assertIsNone(make_share_token({}))

    def test_tampered_token_rejected(self):
        token = make_share_token(self._context())
        with self.assertRaises(ShareTokenError):
            read_share_token(token[:-1] + ('a' if token[-1] != 'a' else 'b'))

    def test_garbage_token_rejected(self):
        with self.assertRaises(ShareTokenError):
            read_share_token('not-a-token')

    @override_settings(FOODIE_SHARE_MAX_AGE_DAYS=7)
    def test_expired_token_rejected(self):
        token = make_share_token(self._context())
        eight_days = 8 * 86400
        with patch('django.core.signing.time.time', return_value=time_module.time() + eight_days):
            with self.assertRaises(ShareTokenExpired):
                read_share_token(token)

    @override_settings(FOODIE_SHARE_MAX_AGE_DAYS=30)
    def test_max_age_comes_from_settings(self):
        token = make_share_token(self._context())
        eight_days = 8 * 86400
        with patch('django.core.signing.time.time', return_value=time_module.time() + eight_days):
            self.assertEqual(read_share_token(token)['option_1']['id'], self.m1.id)

    def test_deleted_meals_rejected(self):
        token = make_share_token(_build_context('lunch', self.m1, None, None))
        self.m1.delete()
        with self.assertRaises(ShareTokenError):
            read_share_token(token)

    def test_deleted_option_1_falls_back_to_fancy(self):
        token = make_share_token(self._context())
        self.m1.delete()
        self.m2.delete()
        restored = read_share_token(token)

        self.assertEqual(restored['fancy']['id'], self.fancy_meal.id)
        self.assertNotIn('option_1', restored)


class SharedSuggestionViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lunch = MealTimeSlot.objects.create(label='lunch', default_time=time(13, 0))
        cls.m1 = meal.objects.create(name='Jollof')

    def test_shared_link_renders_the_shared_meals(self):
        token = make_share_token(_build_context('lunch', self.m1, None, None))
        response = self.client.get(reverse('foodie_shared', kwargs={'token': token}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_shared'])
        self.assertEqual(response.context['option_1']['id'], self.m1.id)
        self.assertNotIn('share_url', response.context)

    def test_bad_token_returns_404_page(self):
        response = self.client.get(reverse('foodie_shared', kwargs={'token': 'garbage'}))

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'foodie/shared_unavailable.html')
        self.assertFalse(response.context['expired'])

    @override_settings(FOODIE_SHARE_MAX_AGE_DAYS=7)
    def test_expired_token_returns_410_page(self):
        token = make_share_token(_build_context('lunch', self.m1, None, None))
        with patch('django.core.signing.time.time', return_value=time_module.time() + 8 * 86400):
            response = self.client.get(reverse('foodie_shared', kwargs={'token': token}))

        self.assertEqual(response.status_code, 410)
        self.assertTrue(response.context['expired'])

    def test_foodie_page_exposes_a_share_url(self):
        user = get_user_model().objects.create_user(username='viewer', password='pw')
        userPreference.objects.create(user=user, meal=self.m1, slot=self.lunch)
        UserMealSchedule.objects.update_or_create(
            user=user, slot=self.lunch, defaults={'time': time(13, 0)}
        )
        self.client.force_login(user)

        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(13, 30)
            response = self.client.get(reverse('foodie'))

        share_url = response.context['share_url']
        self.assertIn('/foodie/s/', share_url)
        restored = read_share_token(share_url.rstrip('/').rsplit('/', 1)[1])
        self.assertEqual(restored['option_1']['id'], self.m1.id)
