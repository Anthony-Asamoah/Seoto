import logging
from datetime import datetime

from django.db import transaction as db_transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .models import (
    RecurringOccurrenceStatusChoices,
    RecurringTransaction,
    RecurringTransactionOccurrence,
    Transaction,
)

logger = logging.getLogger(__name__)

# Safety cap on catch-up iterations in a single call (e.g. a schedule that was
# paused for a long time), well over a year of daily occurrences.
MAX_OCCURRENCES_PER_RUN = 366


def create_transaction_from_recurring(recurring_transaction, scheduled_date):
    """Create a Transaction verbatim from a RecurringTransaction's template fields.

    This is the auto-renew path, where no user is present to ask. A manual approval goes
    through `ConfirmOccurrenceForm` instead, which lets the user edit the amount and the
    rest before the transaction exists.

    `scheduled_date` is the occurrence's due date, not the moment this function actually runs —
    those two differ for a backdated catch-up run (several occurrences processed together, long
    after they were due), and the transaction should record the date it was due, not the
    processing time; it is stamped with the schedule's `run_time`.
    """
    transaction_time = timezone.make_aware(datetime.combine(scheduled_date, recurring_transaction.run_time))
    transaction = Transaction.objects.create(
        mode=recurring_transaction.mode,
        amount=recurring_transaction.amount,
        currency=recurring_transaction.currency,
        details=recurring_transaction.details,
        reference=recurring_transaction.reference,
        account=recurring_transaction.account,
        destination_account=recurring_transaction.destination_account,
        category=recurring_transaction.category,
        transaction_time=transaction_time,
        attachment=None,
    )
    transaction.tags.set(recurring_transaction.tags.all())
    return transaction


def process_due_occurrences(recurring_transaction, now=None):
    """
    Create RecurringTransactionOccurrence rows for every occurrence due by `now` (local),
    acting on each per `is_auto_renew`. Idempotent: re-processing a date that
    already has an occurrence (e.g. the daily command running after this was
    already handled at save-time) is a no-op for that date, thanks to the
    unique_together constraint on (recurring_transaction, scheduled_date).
    """
    from domains.pwa.services import enqueue_push_notification

    now = now or timezone.localtime()
    iterations = 0

    while recurring_transaction.is_due(now):
        iterations += 1
        if iterations > MAX_OCCURRENCES_PER_RUN:
            logger.warning(
                "RecurringTransaction %s exceeded max catch-up iterations; stopping early",
                recurring_transaction.pk,
            )
            break

        occurrence, created = RecurringTransactionOccurrence.objects.get_or_create(
            recurring_transaction=recurring_transaction,
            scheduled_date=recurring_transaction.next_run_date,
        )

        if created:
            # `details` holds Quill-authored rich text (HTML); notifications are plain text.
            # Only shown when it says something the mode label doesn't already say.
            plain_details = ' '.join(strip_tags(recurring_transaction.details or '').split())
            mode_label = recurring_transaction.get_mode_display()
            description_suffix = f' — {plain_details}' if plain_details else ''
            amount_label = f'{recurring_transaction.currency} {recurring_transaction.amount}'
            note = recurring_transaction.notification_note
            note_suffix = f' ({note})' if note else ''

            if recurring_transaction.is_auto_renew:
                with db_transaction.atomic():
                    created_transaction = create_transaction_from_recurring(recurring_transaction, occurrence.scheduled_date)
                    occurrence.status = RecurringOccurrenceStatusChoices.AUTO_CREATED
                    occurrence.transaction = created_transaction
                    occurrence.resolved_at = timezone.now()
                    occurrence.save()
                enqueue_push_notification(
                    user=recurring_transaction.user,
                    title='Recurring Transaction Created',
                    body=f'{mode_label}: {amount_label}{description_suffix}{note_suffix}',
                    url=f'/spending_tracker/transactions/?highlight={created_transaction.pk}',
                )
            else:
                enqueue_push_notification(
                    user=recurring_transaction.user,
                    title='Recurring Transaction Due',
                    body=f'Approve creating {amount_label} {mode_label}{description_suffix}?{note_suffix}',
                    url=reverse('spending_tracker:confirm_recurring_occurrence', args=[occurrence.pk]),
                )

        recurring_transaction.last_run_at = timezone.now()
        recurring_transaction.advance_next_run_date()
        recurring_transaction.save()


def process_all_due_recurring_transactions(now=None):
    """Process every active schedule whose date and `run_time` have passed, returning how many were handled."""
    now = now or timezone.localtime()
    due_schedules = RecurringTransaction.objects.filter(is_active=True).filter(
        Q(next_run_date__lt=now.date()) | Q(next_run_date=now.date(), run_time__lte=now.time())
    )

    processed = 0
    for pk in list(due_schedules.values_list('pk', flat=True)):
        with db_transaction.atomic():
            # Re-checked under the row lock, so an overlapping tick that got there first leaves nothing to do.
            recurring_transaction = RecurringTransaction.objects.select_for_update(skip_locked=True).filter(pk=pk).first()
            if recurring_transaction is None or not recurring_transaction.is_due(now):
                continue
            process_due_occurrences(recurring_transaction, now=now)
        processed += 1

    return processed
