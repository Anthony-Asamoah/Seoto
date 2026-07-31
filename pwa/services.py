import json

from django.conf import settings
from pywebpush import webpush, WebPushException

from pwa.models import Notification, PushSubscription
from pwa.views import logger


def send_push_notification(user, title, body, icon=None, url=None, data=None):
    """
    Send push notification to all user's active subscriptions.

    Args:
        user: User object
        title: Notification title
        body: Notification body
        icon: Icon URL (optional)
        url: URL to open on click (optional)
        data: Additional data (optional)
    """
    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        icon=icon or '/static/img/pwa/android-chrome-192x192.png',
        url=url,
        data=data or {}
    )

    subscriptions = list(PushSubscription.objects.filter(user=user, is_active=True))
    if not subscriptions: return 0

    payload = json.dumps({
        'title': title,
        'body': body,
        'icon': icon or '/static/img/pwa/android-chrome-192x192.png',
        'badge': '/static/img/pwa/favicon-32x32.png',
        'data': {
            'url': url or '/',
            **(data or {})
        }
    })

    # VAPID_PRIVATE_KEY is a single-line raw base64url EC scalar. pywebpush sees it is not a
    # file path and routes it through Vapid.from_string -> from_raw. (See generate_vapid_keys.)
    success_count = 0
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription.get_subscription_info(),
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"}
            )
            success_count += 1
        except WebPushException as e:
            response_status = e.response.status_code if e.response else 'no response'
            logger.error(f"Push failed for subscription {subscription.id} — status: {response_status}, error: {e}")
            if e.response and e.response.status_code in [404, 410]:
                subscription.is_active = False
                subscription.save()
        except Exception:
            logger.exception(f"Unexpected push error for subscription {subscription.id}")

    if success_count > 0:
        from django.utils import timezone
        notification.sent = True
        notification.sent_at = timezone.now()
        notification.save()

    return success_count
