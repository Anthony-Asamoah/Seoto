import logging

from celery import shared_task

from .runner import run_due_jobs

logger = logging.getLogger(__name__)


@shared_task
def run_due_jobs_task():
    """Beat's once-a-minute tick; dueness, misfires and coalescing stay in the runner."""
    results = run_due_jobs()
    for entry in results:
        if entry['status'] != 'skipped':
            logger.info('Scheduled job %s %s: %s', entry['id'], entry['status'], entry['result'])
    return results
