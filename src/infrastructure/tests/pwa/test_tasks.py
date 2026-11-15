from unittest.mock import Mock, patch

from celery.exceptions import Retry
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from pywebpush import WebPushException
from requests import Response

from domains.pwa.models import Notification, PushSubscription
from domains.pwa.services import enqueue_push_notification
from domains.pwa.tasks import deliver_notification_task

from .helpers import RAW_VAPID_PRIVATE_KEY


@override_settings(VAPID_PRIVATE_KEY=RAW_VAPID_PRIVATE_KEY, VAPID_ADMIN_EMAIL='admin@seoto.org')
class DeliverNotificationTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tasker', password='pass')
        PushSubscription.objects.create(user=self.user, endpoint='https://push.example.com/a', p256dh='k', auth='a')

    def _notification(self):
        return Notification.objects.create(user=self.user, title='t', body='b')

    def _failing(self, status):
        response = Response()
        response.status_code = status
        return Mock(side_effect=WebPushException('boom', response=response))

    @patch('domains.pwa.services.webpush')
    def test_enqueue_delivers_after_commit(self, webpush):
        run_inline = lambda pk: deliver_notification_task.apply(args=[pk])
        with patch.object(deliver_notification_task, 'delay', side_effect=run_inline), self.captureOnCommitCallbacks(execute=True):
            notification = enqueue_push_notification(self.user, 't', 'b')
            webpush.assert_not_called()

        self.assertEqual(webpush.call_count, 1)
        notification.refresh_from_db()
        self.assertTrue(notification.sent)

    @patch('domains.pwa.services.webpush')
    def test_already_sent_notification_is_not_redelivered(self, webpush):
        notification = self._notification()
        deliver_notification_task.apply(args=[notification.pk])
        deliver_notification_task.apply(args=[notification.pk])

        self.assertEqual(webpush.call_count, 1)

    def test_transient_failure_retries(self):
        notification = self._notification()
        with patch('domains.pwa.services.webpush', self._failing(503)), \
                patch.object(deliver_notification_task, 'retry', side_effect=Retry()) as retry:
            with self.assertLogs('domains.pwa.services', level='ERROR'):
                with self.assertRaises(Retry):
                    deliver_notification_task.apply(args=[notification.pk], throw=True)

        retry.assert_called_once()

    def test_dead_subscription_is_not_retried(self):
        notification = self._notification()
        with patch('domains.pwa.services.webpush', self._failing(410)), \
                patch.object(deliver_notification_task, 'retry') as retry:
            with self.assertLogs('domains.pwa.services', level='ERROR'):
                deliver_notification_task.apply(args=[notification.pk], throw=True)

        retry.assert_not_called()


class FailedFlagTests(TestCase):
    def test_exhausted_retries_mark_the_notification_failed(self):
        from celery.exceptions import MaxRetriesExceededError

        user = User.objects.create_user(username='failer', password='pass')
        PushSubscription.objects.create(user=user, endpoint='https://push.example.com/f', p256dh='k', auth='a')
        notification = Notification.objects.create(user=user, title='t', body='b')
        response = Response()
        response.status_code = 503

        with patch('domains.pwa.services.webpush', Mock(side_effect=WebPushException('boom', response=response))), \
                patch.object(deliver_notification_task, 'retry', side_effect=MaxRetriesExceededError()), \
                self.assertLogs('domains.pwa.services', level='ERROR'):
            deliver_notification_task.apply(args=[notification.pk])

        notification.refresh_from_db()
        self.assertTrue(notification.failed)
        self.assertFalse(notification.sent)
