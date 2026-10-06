from datetime import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from domains.apps.foodie.models import MealTimeSlot, UserMealSchedule, meal

from .helpers import _at

CONFIGURE_PROMPT = 'Configure your cuisine'


class EmptyMenuViewTests(TestCase):
    def _get_foodie_at(self, hour):
        with patch('domains.apps.foodie.services.datetime') as mock_dt:
            mock_dt.now.return_value = _at(hour)
            return self.client.get(reverse('foodie'))

    def test_anonymous_off_hours_gets_a_stable_fancy_suggestion(self):
        fancy_meals = [meal.objects.create(name=f'Fancy{i}', is_fancy=True) for i in range(5)]

        first = self._get_foodie_at(23)
        second = self._get_foodie_at(23)

        self.assertNotContains(first, CONFIGURE_PROMPT)
        self.assertIn(first.context['fancy']['id'], {m.id for m in fancy_meals})
        self.assertEqual(first.context['fancy']['id'], second.context['fancy']['id'])
        self.assertContains(first, escape(first.context['suggestion_text']))
        self.assertIn('share_url', first.context)

    def test_anonymous_slot_without_meals_falls_back_to_fancy(self):
        fancy_meal = meal.objects.create(name='Sushi', is_fancy=True)

        response = self._get_foodie_at(12)

        self.assertEqual(response.context['fancy']['id'], fancy_meal.id)
        self.assertNotIn('option_1', response.context)
        self.assertIn('for lunch', response.context['suggestion_text'])

    def test_anonymous_with_nothing_at_all_hides_configure_prompt(self):
        response = self._get_foodie_at(23)

        self.assertNotContains(response, CONFIGURE_PROMPT)
        self.assertContains(response, "The kitchen's closed")

    def test_authenticated_with_nothing_sees_configure_prompt(self):
        user = get_user_model().objects.create_user(username='hungry', password='pw')
        lunch = MealTimeSlot.objects.create(label='lunch', default_time=time(12, 0))
        UserMealSchedule.objects.update_or_create(user=user, slot=lunch, defaults={'time': time(12, 0)})
        self.client.force_login(user)

        response = self._get_foodie_at(12)

        self.assertContains(response, CONFIGURE_PROMPT)
