from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from pywebpush import WebPushException
from requests import Response

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


@override_settings(
    VAPID_PRIVATE_KEY=RAW_VAPID_PRIVATE_KEY,
    VAPID_ADMIN_EMAIL='admin@seoto.org',
)
class DeadSubscriptionPruningTest(TestCase):
    """A push endpoint reporting the subscription is gone must deactivate it.

    Pins `is not None` over truthiness: an error Response is falsy, so a 410 would repeat forever.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='pruner', password='pass')
        self.sub = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://push.example.com/dead',
            p256dh='p256dh-key',
            auth='auth-secret',
        )

    def _failing_webpush(self, status_code):
        response = Response()
        response.status_code = status_code
        exception = WebPushException('Push failed', response=response)
        return Mock(side_effect=exception)

    def _send(self):
        return send_push_notification(user=self.user, title='t', body='b')

    def test_410_gone_deactivates_the_subscription(self):
        with patch('domains.pwa.services.webpush', self._failing_webpush(410)):
            with self.assertLogs('domains.pwa.views', level='ERROR') as logs:
                sent = self._send()

        self.sub.refresh_from_db()
        self.assertEqual(sent, 0)
        self.assertFalse(self.sub.is_active)
        self.assertIn('status: 410', logs.output[0])

    def test_404_not_found_deactivates_the_subscription(self):
        with patch('domains.pwa.services.webpush', self._failing_webpush(404)):
            with self.assertLogs('domains.pwa.views', level='ERROR'):
                self._send()

        self.sub.refresh_from_db()
        self.assertFalse(self.sub.is_active)

    def test_transient_failure_keeps_the_subscription(self):
        with patch('domains.pwa.services.webpush', self._failing_webpush(503)):
            with self.assertLogs('domains.pwa.views', level='ERROR'):
                self._send()

        self.sub.refresh_from_db()
        self.assertTrue(self.sub.is_active)

    def test_failure_without_a_response_is_logged_and_kept(self):
        exception = WebPushException('no response at all')
        with patch('domains.pwa.services.webpush', Mock(side_effect=exception)):
            with self.assertLogs('domains.pwa.views', level='ERROR') as logs:
                self._send()

        self.sub.refresh_from_db()
        self.assertTrue(self.sub.is_active)
        self.assertIn('status: no response', logs.output[0])

    def test_a_dead_subscription_does_not_block_a_live_one(self):
        live = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://push.example.com/live',
            p256dh='p256dh-key-2',
            auth='auth-secret-2',
        )
        dead_response = Response()
        dead_response.status_code = 410

        def webpush(subscription_info, **kwargs):
            if subscription_info['endpoint'] == self.sub.endpoint:
                raise WebPushException('Push failed', response=dead_response)
            return None

        with patch('domains.pwa.services.webpush', side_effect=webpush):
            with self.assertLogs('domains.pwa.views', level='ERROR'):
                sent = self._send()

        self.sub.refresh_from_db()
        live.refresh_from_db()
        self.assertEqual(sent, 1)
        self.assertFalse(self.sub.is_active)
        self.assertTrue(live.is_active)
