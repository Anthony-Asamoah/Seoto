from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from .models import Notification
from .services import deliver_notification

MAX_RETRIES = 3


@shared_task(bind=True, max_retries=MAX_RETRIES)
def deliver_notification_task(self, notification_id):
    notification = Notification.objects.select_related('user').filter(pk=notification_id, sent=False).first()
    if notification is None:
        return 0

    delivered, transient = deliver_notification(notification)
    if not delivered and transient:
        # Only when nothing got through, so a retry cannot double-deliver to a subscription that already did.
        try:
            raise self.retry(countdown=60 * 2 ** self.request.retries)
        except MaxRetriesExceededError:
            Notification.objects.filter(pk=notification.pk).update(failed=True)
            raise
    return delivered
