from django.conf import settings
from django.test import SimpleTestCase

from config.celery import app


class BeatScheduleTests(SimpleTestCase):
    def test_every_scheduled_task_is_registered(self):
        app.loader.import_default_modules()
        task_names = {entry['task'] for entry in settings.CELERY_BEAT_SCHEDULE.values()}

        self.assertEqual(len(task_names), 3)
        self.assertTrue(task_names <= set(app.tasks), task_names - set(app.tasks))
