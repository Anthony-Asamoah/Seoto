from django.db import transaction
from django.db.models import F
from django.utils import timezone

from domains.pwa.services import enqueue_push_notification

from .models import todo


def send_due_todo_reminders(now=None):
    """Claim each open todo whose reminder has passed, once per reminder value, and queue its push; returns how many."""
    now = now or timezone.now()
    with transaction.atomic():
        due = list(
            todo.objects.select_for_update(skip_locked=True).select_related('user')
            .filter(reminder__lte=now, isCompleted=False)
            .exclude(reminded_for=F('reminder'))
        )
        for item in due:
            enqueue_push_notification(user=item.user, title='Reminder', body=item.title, url='/jotter/')
            item.reminded_for = item.reminder
            item.save(update_fields=['reminded_for'])

    return len(due)
