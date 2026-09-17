from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from domains.pwa.models import Notification, PushSubscription
from domains.pwa.services import send_push_notification

from .helpers import RAW_VAPID_PRIVATE_KEY


@override_settings(
    VAPID_PRIVATE_KEY=RAW_VAPID_PRIVATE_KEY,
    VAPID_ADMIN_EMAIL='admin@seoto.org',
)
class SendPushNotificationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pass')
        self.sub = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://push.example.com/sub-1',
            p256dh='p256dh-key',
            auth='auth-secret',
        )

    @patch('domains.pwa.services.webpush')
    def test_passes_raw_private_key_string_directly(self, mock_webpush):
        count = send_push_notification(self.user, 'Hi', 'Body')

        self.assertEqual(count, 1)
        self.assertEqual(mock_webpush.call_count, 1)
        kwargs = mock_webpush.call_args.kwargs
        # The raw key string is handed to pywebpush as-is — not a temp .pem path.
        self.assertEqual(kwargs['vapid_private_key'], RAW_VAPID_PRIVATE_KEY)
        self.assertFalse(kwargs['vapid_private_key'].endswith('.pem'))
        self.assertEqual(kwargs['vapid_claims'], {'sub': 'mailto:admin@seoto.org'})
        self.assertEqual(kwargs['subscription_info'], self.sub.get_subscription_info())

    @patch('domains.pwa.services.webpush')
    def test_calls_webpush_once_per_active_subscription(self, mock_webpush):
        PushSubscription.objects.create(
            user=self.user,
            endpoint='https://push.example.com/sub-2',
            p256dh='p256dh-key-2',
            auth='auth-secret-2',
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint='https://push.example.com/sub-inactive',
            p256dh='p256dh-key-3',
            auth='auth-secret-3',
            is_active=False,
        )

        count = send_push_notification(self.user, 'Hi', 'Body')

        self.assertEqual(count, 2)
        self.assertEqual(mock_webpush.call_count, 2)

    @patch('domains.pwa.services.webpush')
    def test_marks_notification_sent_on_success(self, mock_webpush):
        send_push_notification(self.user, 'Hi', 'Body')
        notification = Notification.objects.get(user=self.user, title='Hi')
        self.assertTrue(notification.sent)
        self.assertIsNotNone(notification.sent_at)
