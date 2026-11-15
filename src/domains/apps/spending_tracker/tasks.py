from celery import shared_task

from common.heartbeat import heartbeat

from .services import process_all_due_recurring_transactions


@shared_task
@heartbeat
def process_recurring_transactions():
    return process_all_due_recurring_transactions()
