from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase

from config.celery import app
from infrastructure.scheduler import tasks


class RunDueJobsTaskTests(SimpleTestCase):
    def test_beat_schedule_points_at_a_registered_task(self):
        task_names = {entry['task'] for entry in settings.CELERY_BEAT_SCHEDULE.values()}

        self.assertIn('infrastructure.scheduler.tasks.run_due_jobs_task', task_names)
        self.assertTrue(task_names <= set(app.tasks))

    def test_tick_delegates_to_the_runner(self):
        results = [{'id': 'hourly', 'status': 'ran', 'result': 3}]
        with mock.patch.object(tasks, 'run_due_jobs', return_value=results) as run:
            self.assertEqual(tasks.run_due_jobs_task.apply().get(), results)

        run.assert_called_once_with()
