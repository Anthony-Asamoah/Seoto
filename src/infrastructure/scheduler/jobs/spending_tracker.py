import logging

from django.conf import settings

from domains.apps.spending_tracker.services import process_all_due_recurring_transactions
from infrastructure.scheduler import scheduled_job

logger = logging.getLogger(__name__)

DEFAULT_RECURRING_HOUR = 19


def _recurring_hour():
    """The hour field of RECURRING_TRANSACTIONS_CRON, which stays the env-facing knob."""
    cron_expression = getattr(settings, 'RECURRING_TRANSACTIONS_CRON', '0 19 * * *')
    try:
        _minute, hour, *_rest = cron_expression.split()
        return int(hour)
    except (ValueError, AttributeError):
        logger.warning(
            "Could not parse RECURRING_TRANSACTIONS_CRON=%r; falling back to hour %s",
            cron_expression, DEFAULT_RECURRING_HOUR,
        )
        return DEFAULT_RECURRING_HOUR


@scheduled_job(
    trigger='cron',
    id='process_recurring_transactions',
    hour=_recurring_hour(),
    minute=0,
)
def process_recurring_transactions():
    return process_all_due_recurring_transactions()
