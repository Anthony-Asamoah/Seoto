from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from pwa.models import Notification, PushSubscription
from pwa.services import send_push_notification


class NotificationsListViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pass')
        self.url = reverse('pwa:notifications_list')

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, '/accounts/login/?next=' + self.url, fetch_redirect_response=False)

    def test_returns_json_for_authenticated_user(self):
        self.client.login(username='tester', password='pass')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertIn('notifications', data)
        self.assertIn('unread_count', data)
        self.assertIsInstance(data['notifications'], list)

    def test_returns_empty_list_when_no_notifications(self):
        self.client.login(username='tester', password='pass')
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(data['notifications'], [])
        self.assertEqual(data['unread_count'], 0)

    def test_returns_up_to_10_notifications(self):
        self.client.login(username='tester', password='pass')
        for i in range(15):
            Notification.objects.create(user=self.user, title=f'Notif {i}', body='body')
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(len(data['notifications']), 10)

    def test_notification_shape(self):
        self.client.login(username='tester', password='pass')
        Notification.objects.create(user=self.user, title='Test', body='Body', url='/some/path/')
        response = self.client.get(self.url)
        notif = response.json()['notifications'][0]
        for key in ('id', 'title', 'body', 'url', 'is_read', 'created_at'):
            self.assertIn(key, notif)
        self.assertEqual(notif['title'], 'Test')
        self.assertEqual(notif['url'], '/some/path/')

    def test_unread_count_reflects_unread_notifications(self):
        self.client.login(username='tester', password='pass')
        Notification.objects.create(user=self.user, title='Unread', body='body', is_read=False)
        Notification.objects.create(user=self.user, title='Read', body='body', is_read=True)
        response = self.client.get(self.url)
        data = response.json()
        self.assertEqual(data['unread_count'], 1)

    def test_only_returns_own_notifications(self):
        other = User.objects.create_user(username='other', password='pass')
        Notification.objects.create(user=other, title='Other user notif', body='body')
        self.client.login(username='tester', password='pass')
        response = self.client.get(self.url)
        self.assertEqual(response.json()['notifications'], [])


class MarkNotificationsReadViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pass')
        self.url = reverse('pwa:mark_notifications_read')

    def test_requires_login(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, '/accounts/login/?next=' + self.url, fetch_redirect_response=False)

    def test_marks_all_unread_as_read(self):
        self.client.login(username='tester', password='pass')
        Notification.objects.create(user=self.user, title='A', body='b', is_read=False)
        Notification.objects.create(user=self.user, title='B', body='b', is_read=False)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True})
        self.assertEqual(self.user.notifications.filter(is_read=False).count(), 0)


# A single-line raw base64url key (shape only; webpush is mocked so it is never deserialized).
RAW_VAPID_PRIVATE_KEY = 'k3Pq0p6h1xq8nKxqHc3lQwZ2Z5Yt0Xy9aB1cD2eF3g'


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

    @patch('pwa.services.webpush')
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

    @patch('pwa.services.webpush')
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

    @patch('pwa.services.webpush')
    def test_marks_notification_sent_on_success(self, mock_webpush):
        send_push_notification(self.user, 'Hi', 'Body')
        notification = Notification.objects.get(user=self.user, title='Hi')
        self.assertTrue(notification.sent)
        self.assertIsNotNone(notification.sent_at)
