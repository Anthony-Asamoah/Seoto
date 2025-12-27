from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from pywebpush import webpush, WebPushException
import json
from .models import PushSubscription, Notification


@require_http_methods(["GET"])
def vapid_public_key(request):
    """Return VAPID public key for push subscription"""
    return JsonResponse({
        'publicKey': settings.VAPID_PUBLIC_KEY
    })


@login_required
@require_http_methods(["POST"])
def subscribe_push(request):
    """Subscribe user to push notifications"""
    try:
        subscription_data = json.loads(request.body)

        # Extract subscription details
        endpoint = subscription_data.get('endpoint')
        keys = subscription_data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not all([endpoint, p256dh, auth]):
            return JsonResponse({'error': 'Missing subscription data'}, status=400)

        # Create or update subscription
        subscription, created = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh': p256dh,
                'auth': auth,
                'is_active': True
            }
        )

        return JsonResponse({
            'success': True,
            'created': created
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def unsubscribe_push(request):
    """Unsubscribe user from push notifications"""
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')

        if not endpoint:
            return JsonResponse({'error': 'Missing endpoint'}, status=400)

        PushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint
        ).update(is_active=False)

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def send_push_notification(user, title, body, icon=None, url=None, data=None):
    """
    Send push notification to all user's active subscriptions

    Args:
        user: User object
        title: Notification title
        body: Notification body
        icon: Icon URL (optional)
        url: URL to open on click (optional)
        data: Additional data (optional)
    """
    # Create notification record
    notification = Notification.objects.create(
        user=user,
        title=title,
        body=body,
        icon=icon or '/static/img/pwa/icon-192x192.png',
        url=url,
        data=data or {}
    )

    # Get all active subscriptions for user
    subscriptions = PushSubscription.objects.filter(
        user=user,
        is_active=True
    )

    # Prepare notification payload
    payload = {
        'title': title,
        'body': body,
        'icon': icon or '/static/img/pwa/icon-192x192.png',
        'badge': '/static/img/pwa/icon-72x72.png',
        'data': {
            'url': url or '/',
            **(data or {})
        }
    }

    # Send to all subscriptions
    success_count = 0
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription.get_subscription_info(),
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"
                }
            )
            success_count += 1
        except WebPushException as e:
            print(f"Push failed for {subscription.endpoint}: {e}")
            if e.response and e.response.status_code in [404, 410]:
                # Subscription no longer valid
                subscription.is_active = False
                subscription.save()

    # Update notification record
    if success_count > 0:
        from django.utils import timezone
        notification.sent = True
        notification.sent_at = timezone.now()
        notification.save()

    return success_count
