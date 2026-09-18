from datetime import datetime, timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from domains.home.models import ScheduledJobRun
from infrastructure.scheduler import registry, runner

# At module load, so the real jobs register before any test patches SCHEDULED_JOBS.
import infrastructure.scheduler.jobs  # noqa: E402,F401


def _at(hour, minute=0):
    return timezone.make_aware(datetime(2026, 9, 17, hour, minute))


class RunnerTestCase(TestCase):
    def setUp(self):
        for module in (registry, runner):
            patcher = mock.patch.object(module, 'SCHEDULED_JOBS', [])
            patcher.start()
            self.addCleanup(patcher.stop)
        runner.SCHEDULED_JOBS = registry.SCHEDULED_JOBS

    def register(self, job_id, func=None, **kwargs):
        kwargs.setdefault('trigger', 'cron')
        registry.scheduled_job(id=job_id, **kwargs)(func or (lambda: 'done'))

    def state(self, job_id):
        return ScheduledJobRun.objects.get(job_id=job_id)


class FirstSightTests(RunnerTestCase):
    def test_a_new_job_is_scheduled_ahead_and_does_not_fire_immediately(self):
        self.register('hourly', hour='*', minute=0)

        results = runner.run_due_jobs(now=_at(10, 30))

        self.assertEqual(results[0]['status'], 'skipped')
        self.assertEqual(self.state('hourly').next_run_at, _at(11, 0))

    def test_state_is_created_once_not_per_tick(self):
        self.register('hourly', hour='*', minute=0)
        runner.run_due_jobs(now=_at(10, 30))
        runner.run_due_jobs(now=_at(10, 45))
        self.assertEqual(ScheduledJobRun.objects.filter(job_id='hourly').count(), 1)


class TickRateTests(RunnerTestCase):
    """The same schedule must hold whatever cadence the runner is invoked at."""

    def _run_across_a_day(self, tick_minutes):
        registry.SCHEDULED_JOBS.clear()
        ScheduledJobRun.objects.all().delete()

        calls = []
        self.register('hourly', lambda: calls.append(1), hour='*', minute=0)

        start = _at(0, 0)
        runner.run_due_jobs(now=start)

        tick = start
        end = start + timedelta(days=1)
        while tick < end:
            tick += timedelta(minutes=tick_minutes)
            runner.run_due_jobs(now=tick)
        return len(calls)

    def test_an_hourly_job_fires_24_times_a_day_at_every_tick_rate(self):
        for tick_minutes in (1, 5, 15, 60):
            with self.subTest(tick_minutes=tick_minutes):
                self.assertEqual(self._run_across_a_day(tick_minutes), 24)

    def test_a_job_fires_once_even_when_the_tick_straddles_its_time(self):
        calls = []
        self.register('evening', lambda: calls.append(1), hour=19, minute=0)

        runner.run_due_jobs(now=_at(18, 50))
        # A 15-minute tick never lands exactly on 19:00.
        runner.run_due_jobs(now=_at(19, 5))
        runner.run_due_jobs(now=_at(19, 20))

        self.assertEqual(len(calls), 1)
        self.assertEqual(self.state('evening').next_run_at, _at(19, 0) + timedelta(days=1))


class CoalescingTests(RunnerTestCase):
    def test_a_long_outage_causes_one_run_not_a_backlog(self):
        calls = []
        self.register('hourly', lambda: calls.append(1), hour='*', minute=0)

        runner.run_due_jobs(now=_at(1, 0))
        # Nothing invokes the runner for eight hours.
        runner.run_due_jobs(now=_at(9, 30))

        self.assertEqual(len(calls), 1)
        self.assertEqual(self.state('hourly').next_run_at, _at(10, 0))


class MisfireTests(RunnerTestCase):
    def test_a_run_later_than_its_grace_is_skipped_and_rescheduled(self):
        calls = []
        self.register('hourly', lambda: calls.append(1), hour='*', minute=0, misfire_grace=30 * 60)

        runner.run_due_jobs(now=_at(1, 0))
        with self.assertLogs('infrastructure.scheduler.runner', level='WARNING'):
            results = runner.run_due_jobs(now=_at(3, 45))

        self.assertEqual(results[0]['status'], 'misfired')
        self.assertEqual(calls, [])
        self.assertEqual(self.state('hourly').next_run_at, _at(4, 0))
        self.assertIsNone(self.state('hourly').last_run_at)

    def test_a_run_inside_its_grace_still_happens(self):
        calls = []
        self.register('hourly', lambda: calls.append(1), hour='*', minute=0, misfire_grace=30 * 60)

        runner.run_due_jobs(now=_at(1, 0))
        results = runner.run_due_jobs(now=_at(2, 20))

        self.assertEqual(results[0]['status'], 'ran')
        self.assertEqual(len(calls), 1)

    def test_without_a_grace_a_late_run_still_happens(self):
        calls = []
        self.register('daily', lambda: calls.append(1), hour=19, minute=0)

        runner.run_due_jobs(now=_at(18, 0))
        runner.run_due_jobs(now=_at(23, 59))

        self.assertEqual(len(calls), 1)


class FailureTests(RunnerTestCase):
    def test_a_failing_job_does_not_stop_the_others_and_still_advances(self):
        def boom():
            raise RuntimeError('kaboom')

        self.register('bad', boom, hour='*', minute=0)
        self.register('good', hour='*', minute=0)

        runner.run_due_jobs(now=_at(10, 30))
        with self.assertLogs('infrastructure.scheduler.runner', level='ERROR'):
            results = runner.run_due_jobs(now=_at(11, 0))

        self.assertEqual([e['status'] for e in results], ['error', 'ran'])
        self.assertIn('kaboom', results[0]['result'])
        self.assertEqual(self.state('bad').next_run_at, _at(12, 0))
        self.assertEqual(self.state('bad').last_status, 'error')


class ForcedRunTests(RunnerTestCase):
    def test_forcing_runs_regardless_of_dueness(self):
        self.register('evening', hour=19, minute=0)
        runner.run_due_jobs(now=_at(3, 0))

        results = runner.run_due_jobs(now=_at(3, 0), job_ids=['evening'])

        self.assertEqual([e['status'] for e in results], ['ran'])
        self.assertEqual(results[0]['result'], 'done')

    def test_forcing_does_not_disturb_the_schedule(self):
        self.register('evening', hour=19, minute=0)
        runner.run_due_jobs(now=_at(3, 0))
        before = self.state('evening').next_run_at

        runner.run_due_jobs(now=_at(3, 0), job_ids=['evening'])

        self.assertEqual(self.state('evening').next_run_at, before)

    def test_forcing_runs_only_the_named_job(self):
        self.register('wanted', hour='*', minute=0)
        self.register('other', hour='*', minute=0)

        results = runner.run_due_jobs(now=_at(10, 30), job_ids=['wanted'])

        self.assertEqual([e['id'] for e in results], ['wanted'])

    def test_unknown_job_id_raises(self):
        self.register('known', hour='*', minute=0)
        with self.assertRaises(ValueError):
            runner.run_due_jobs(now=_at(3, 0), job_ids=['nope'])


class RegisteredJobsTests(TestCase):
    def test_the_real_jobs_are_registered_with_workable_triggers(self):
        ids = [job['id'] for job in registry.SCHEDULED_JOBS]
        self.assertEqual(sorted(ids), ['process_recurring_transactions', 'send_meal_notifications'])
        self.assertEqual(len(ids), len(set(ids)), 'job ids must be unique')

        for job in registry.SCHEDULED_JOBS:
            self.assertIsNotNone(runner.next_fire_time(job, _at(0, 0)))
