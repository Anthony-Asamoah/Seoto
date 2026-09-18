import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .registry import SCHEDULED_JOBS
from .triggers import next_fire_time

logger = logging.getLogger(__name__)


def _state_for(job, now):
    """The job's stored state, created on first sight with its next fire scheduled ahead of `now`.

    A newly registered job therefore waits for its next real fire time instead of running
    the moment it is deployed.
    """
    from domains.home.models import ScheduledJobRun

    state, _ = ScheduledJobRun.objects.get_or_create(
        job_id=job['id'],
        defaults={'next_run_at': next_fire_time(job, now)},
    )
    return state


def _is_misfire(job, state, now):
    """Whether the due time is so old that running now would do more harm than skipping."""
    grace_seconds = job.get('misfire_grace')
    if grace_seconds is None:
        return False
    return now - state.next_run_at > timedelta(seconds=grace_seconds)


def _advance(state, job, now, status):
    """Move past every fire time already behind us, so a long outage causes one run, not a backlog."""
    state.next_run_at = next_fire_time(job, now)
    state.last_status = status
    if status in ('ran', 'error'):
        state.last_run_at = now
    state.save()


def run_due_jobs(now=None, job_ids=None):
    """Run every registered job whose stored next-run time has passed, returning a result per job.

    `job_ids` runs those ids regardless of dueness and does not disturb their schedule.
    A failing job never stops the others; it is logged and recorded as `status='error'`.
    """
    import infrastructure.scheduler.jobs  # noqa: F401  — populates SCHEDULED_JOBS

    now = timezone.localtime(now) if now else timezone.localtime()
    forced = set(job_ids) if job_ids else None
    if forced:
        unknown = forced - {job['id'] for job in SCHEDULED_JOBS}
        if unknown:
            raise ValueError(f'Unknown job id(s): {sorted(unknown)}')

    results = []
    for job in SCHEDULED_JOBS:
        if forced is not None:
            if job['id'] in forced:
                results.append(_execute(job, now, persist=False))
            continue
        results.append(_run_if_due(job, now))

    return results


def _execute(job, now, persist, state=None):
    try:
        result = job['func']()
    except Exception as exc:
        logger.exception('Scheduled job %s failed', job['id'])
        if persist:
            _advance(state, job, now, 'error')
        return {'id': job['id'], 'status': 'error', 'result': repr(exc)}

    if persist:
        _advance(state, job, now, 'ran')
    return {'id': job['id'], 'status': 'ran', 'result': result}


def _run_if_due(job, now):
    from domains.home.models import ScheduledJobRun

    _state_for(job, now)

    with transaction.atomic():
        # Locked so two overlapping ticks cannot both claim the same due time.
        state = ScheduledJobRun.objects.select_for_update().get(job_id=job['id'])

        if state.next_run_at > now:
            return {'id': job['id'], 'status': 'skipped', 'result': None}

        if _is_misfire(job, state, now):
            due_at = state.next_run_at
            _advance(state, job, now, 'misfired')
            logger.warning(
                'Scheduled job %s missed its %s run by more than its grace period; skipping',
                job['id'], due_at,
            )
            return {'id': job['id'], 'status': 'misfired', 'result': None}

        return _execute(job, now, persist=True, state=state)
