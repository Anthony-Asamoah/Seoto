from datetime import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from domains.apps.foodie.models import MealTimeSlot, UserMealSchedule, meal, userPreference
from domains.apps.foodie.services import send_due_meal_notifications

from .helpers import _at


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

    def _run(self, hour, minute=0):
        with patch('domains.pwa.services.enqueue_push_notification') as mock_push:
            result = send_due_meal_notifications(now=timezone.make_aware(_at(hour, minute)))
        return result, mock_push

    def test_sends_to_subscribed_user(self):
        self._add_subscription(self.user)
        result, mock_push = self._run(13)

        mock_push.assert_called_once()
        self.assertEqual(result, {'sent': 1, 'skipped': 0})

    def test_not_sent_before_slot_time(self):
        self._add_subscription(self.user)
        result, mock_push = self._run(12, 59)

        mock_push.assert_not_called()
        self.assertEqual(result, {'sent': 0, 'skipped': 0})

    def test_sent_once_per_fire_time(self):
        self._add_subscription(self.user)
        self._run(13, 2)
        result, mock_push = self._run(13, 3)

        mock_push.assert_not_called()
        self.assertEqual(result, {'sent': 0, 'skipped': 0})

    def test_late_beyond_grace_is_skipped(self):
        self._add_subscription(self.user)
        result, mock_push = self._run(13, 31)

        mock_push.assert_not_called()
        self.assertEqual(result, {'sent': 0, 'skipped': 0})

    def test_skips_user_without_active_subscription(self):
        result, mock_push = self._run(13)

        mock_push.assert_not_called()
        self.assertEqual(result, {'sent': 0, 'skipped': 1})
