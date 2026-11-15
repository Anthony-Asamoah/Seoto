from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from domains.apps.jotter.models import todo
from domains.apps.jotter.services import send_due_todo_reminders


class SendDueTodoRemindersTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='jot', password='pw')
        self.now = timezone.now()

    def _todo(self, **kwargs):
        return todo.objects.create(user=self.user, title='Call mum', **kwargs)

    def _run(self):
        with patch('domains.apps.jotter.services.enqueue_push_notification') as push:
            return send_due_todo_reminders(now=self.now), push

    def test_sends_once_when_reminder_passes(self):
        self._todo(reminder=self.now - timedelta(minutes=1))
        count, push = self._run()
        self.assertEqual(count, 1)
        push.assert_called_once()
        self.assertEqual(push.call_args.kwargs['body'], 'Call mum')

        count, push = self._run()
        self.assertEqual(count, 0)
        push.assert_not_called()

    def test_future_completed_and_unset_reminders_are_ignored(self):
        self._todo(reminder=self.now + timedelta(minutes=5))
        self._todo(reminder=self.now - timedelta(minutes=5), isCompleted=True)
        self._todo()
        count, push = self._run()
        self.assertEqual(count, 0)
        push.assert_not_called()

    def test_rescheduled_reminder_fires_again(self):
        item = self._todo(reminder=self.now - timedelta(minutes=10))
        self._run()
        item.reminder = self.now - timedelta(minutes=1)
        item.save()
        count, _ = self._run()
        self.assertEqual(count, 1)
