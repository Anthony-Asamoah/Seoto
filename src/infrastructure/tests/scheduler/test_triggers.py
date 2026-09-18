from datetime import datetime, timedelta

from django.test import SimpleTestCase

from infrastructure.scheduler.triggers import interval_period, next_fire_time


def _at(hour, minute=0, second=0):
    return datetime(2026, 9, 17, hour, minute, second)


class IntervalTriggerTests(SimpleTestCase):
    def test_fires_on_the_period_anchored_to_midnight(self):
        job = {'id': 'j', 'trigger': 'interval', 'minutes': 15}
        self.assertEqual(next_fire_time(job, _at(10, 0)), _at(10, 15))
        self.assertEqual(next_fire_time(job, _at(10, 7)), _at(10, 15))
        self.assertEqual(next_fire_time(job, _at(10, 14, 59)), _at(10, 15))

    def test_fire_time_is_strictly_after_the_given_moment(self):
        job = {'id': 'j', 'trigger': 'interval', 'minutes': 15}
        self.assertEqual(next_fire_time(job, _at(10, 15)), _at(10, 30))

    def test_hours_and_minutes_combine(self):
        job = {'id': 'j', 'trigger': 'interval', 'hours': 1, 'minutes': 30}
        self.assertEqual(next_fire_time(job, _at(0, 0)), _at(1, 30))
        self.assertEqual(next_fire_time(job, _at(1, 30)), _at(3, 0))

    def test_a_period_that_does_not_divide_the_day_restarts_at_midnight(self):
        job = {'id': 'j', 'trigger': 'interval', 'hours': 7}
        self.assertEqual(next_fire_time(job, _at(14, 0)), _at(21, 0))
        self.assertEqual(next_fire_time(job, _at(21, 0)), datetime(2026, 9, 18, 0, 0))

    def test_period_is_summed_across_units(self):
        self.assertEqual(
            interval_period({'id': 'j', 'hours': 1, 'minutes': 2, 'seconds': 3}),
            timedelta(hours=1, minutes=2, seconds=3),
        )

    def test_a_non_positive_interval_raises(self):
        with self.assertRaises(ValueError):
            next_fire_time({'id': 'j', 'trigger': 'interval', 'minutes': 0}, _at(10))


class CronTriggerTests(SimpleTestCase):
    def test_minute_defaults_to_the_top_of_the_hour(self):
        job = {'id': 'j', 'trigger': 'cron', 'hour': '*'}
        self.assertEqual(next_fire_time(job, _at(10, 30)), _at(11, 0))

    def test_a_specific_hour_and_minute(self):
        job = {'id': 'j', 'trigger': 'cron', 'hour': 19, 'minute': 30}
        self.assertEqual(next_fire_time(job, _at(10, 0)), _at(19, 30))
        self.assertEqual(next_fire_time(job, _at(19, 30)), datetime(2026, 9, 18, 19, 30))

    def test_several_hours(self):
        job = {'id': 'j', 'trigger': 'cron', 'hour': [6, 18], 'minute': 0}
        self.assertEqual(next_fire_time(job, _at(0, 0)), _at(6, 0))
        self.assertEqual(next_fire_time(job, _at(6, 0)), _at(18, 0))

    def test_wildcard_minute_fires_every_minute(self):
        job = {'id': 'j', 'trigger': 'cron', 'hour': 10, 'minute': '*'}
        self.assertEqual(next_fire_time(job, _at(10, 30)), _at(10, 31))

    def test_seconds_are_truncated_not_rounded_past_the_fire(self):
        job = {'id': 'j', 'trigger': 'cron', 'hour': '*', 'minute': 0}
        self.assertEqual(next_fire_time(job, _at(10, 59, 30)), _at(11, 0))

    def test_unknown_trigger_raises(self):
        with self.assertRaises(ValueError):
            next_fire_time({'id': 'j', 'trigger': 'yearly'}, _at(0))
