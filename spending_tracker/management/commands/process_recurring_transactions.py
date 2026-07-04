import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from spending_tracker.models import RecurringTransaction
from spending_tracker.services import process_due_occurrences

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Process due recurring transactions: auto-creates the transaction (is_auto_renew=True) "
        "or sends an approval notification (is_auto_renew=False). Intended to run once a day, "
        "e.g. as a PythonAnywhere Scheduled Task at the time configured by RECURRING_TRANSACTIONS_CRON."
    )

    def handle(self, *args, **options):
        self._warn_if_run_time_drifted()

        today = timezone.localdate()
        due_schedules = RecurringTransaction.objects.filter(is_active=True, next_run_date__lte=today)

        processed = 0
        for recurring_transaction in due_schedules:
            process_due_occurrences(recurring_transaction, today=today)
            processed += 1

        self.stdout.write(self.style.SUCCESS(f'Processed {processed} due recurring transaction(s).'))

    def _warn_if_run_time_drifted(self):
        cron_expression = getattr(settings, 'RECURRING_TRANSACTIONS_CRON', '0 19 * * *')
        try:
            _minute, hour, *_rest = cron_expression.split()
            expected_hour = int(hour)
        except (ValueError, AttributeError):
            logger.warning("Could not parse RECURRING_TRANSACTIONS_CRON=%r; skipping drift check", cron_expression)
            return

        current_hour = timezone.localtime().hour
        if abs(current_hour - expected_hour) > 1:
            logger.warning(
                "process_recurring_transactions ran at hour %s, expected around hour %s "
                "(RECURRING_TRANSACTIONS_CRON=%r) — check the PythonAnywhere Scheduled Task time.",
                current_hour, expected_hour, cron_expression,
            )
