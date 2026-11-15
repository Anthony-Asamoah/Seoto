import json
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from pywebpush import webpush, WebPushException

from domains.pwa.models import Notification, PushSubscription

logger = logging.getLogger(__name__)


DEFAULT_ICON = '/static/img/pwa/android-chrome-192x192.png'


def create_notification(user, title, body, icon=None, url=None, data=None):
    return Notification.objects.create(
        user=user, title=title, body=body, icon=icon or DEFAULT_ICON, url=url, data=data or {},
    )


def deliver_notification(notification):
    """Push `notification` to the user's active subscriptions; returns (delivered, transient_failures).

    Subscriptions the push service reports gone (404/410) are deactivated and are not a transient failure.
    """
    subscriptions = list(PushSubscription.objects.filter(user=notification.user, is_active=True))
    if not subscriptions:
        return 0, 0

    payload = json.dumps({
        'title': notification.title,
        'body': notification.body,
        'icon': notification.icon,
        'badge': '/static/img/pwa/favicon-32x32.png',
        'data': {'url': notification.url or '/', **notification.data},
    })

    # VAPID_PRIVATE_KEY is a single-line raw base64url EC scalar. pywebpush sees it is not a
    # file path and routes it through Vapid.from_string -> from_raw. (See generate_vapid_keys.)
    delivered = transient = 0
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription.get_subscription_info(),
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"}
            )
            delivered += 1
        except WebPushException as e:
            # `is not None`: requests.Response.__bool__ is .ok, so an error response is falsy.
            status = e.response.status_code if e.response is not None else None
            logger.error(f"Push failed for subscription {subscription.id} — status: {status or 'no response'}, error: {e}")
            if status in (404, 410):
                subscription.is_active = False
                subscription.save()
            else:
                transient += 1
        except Exception:
            logger.exception(f"Unexpected push error for subscription {subscription.id}")
            transient += 1

    if delivered:
        notification.sent = True
        notification.sent_at = timezone.now()
        notification.save()

    return delivered, transient


def send_push_notification(user, title, body, icon=None, url=None, data=None):
    """Create and deliver a notification inline; returns how many subscriptions received it."""
    return deliver_notification(create_notification(user, title, body, icon, url, data))[0]


def enqueue_push_notification(user, title, body, icon=None, url=None, data=None):
    """Create the notification now and deliver it from a worker once the surrounding transaction commits."""
    from domains.pwa.tasks import deliver_notification_task

    notification = create_notification(user, title, body, icon, url, data)
    transaction.on_commit(lambda: deliver_notification_task.delay(notification.pk))
    return notification
