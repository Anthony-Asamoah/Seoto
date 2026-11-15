from datetime import timedelta

from django.core.cache import cache
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils import timezone

from common.heartbeat import sweeper_status
from domains.apps.jotter.tasks import send_todo_reminders


class HeartbeatTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def _jotter_row(self):
        return next(r for r in sweeper_status() if r['name'] == 'send_todo_reminders')

    def test_never_run_is_stale(self):
        self.assertTrue(self._jotter_row()['stale'])

    def test_running_a_sweeper_records_a_fresh_heartbeat(self):
        from unittest.mock import patch
        with patch('domains.apps.jotter.tasks.send_due_todo_reminders', return_value=0):
            send_todo_reminders()
        self.assertFalse(self._jotter_row()['stale'])

    def test_old_heartbeat_is_stale(self):
        cache.set('heartbeat:send_todo_reminders', timezone.now() - timedelta(minutes=10))
        self.assertTrue(self._jotter_row()['stale'])

    def test_status_template_renders(self):
        html = render_to_string('admin/pwa/sweeper_status.html', {'sweepers': sweeper_status()})
        self.assertIn('send_todo_reminders', html)
        self.assertIn('not running', html)
