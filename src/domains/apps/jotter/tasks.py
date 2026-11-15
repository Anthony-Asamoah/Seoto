from celery import shared_task

from common.heartbeat import heartbeat

from .services import send_due_todo_reminders


@shared_task
@heartbeat
def send_todo_reminders():
    return send_due_todo_reminders()
