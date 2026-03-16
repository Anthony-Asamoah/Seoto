from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_control
from pywebpush import webpush, WebPushException
import json
import logging
import os
from .models import PushSubscription, Notification

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    """Serve service worker from root path to allow site-wide scope"""
    sw_path = os.path.join(settings.BASE_DIR, 'seoto', 'static', 'js', 'sw.js')
    try:
        with open(sw_path, 'r') as f:
            sw_content = f.read()
        response = HttpResponse(sw_content, content_type='application/javascript')
        # Allow service worker to control the entire site
        response['Service-Worker-Allowed'] = '/'
        return response
    except FileNotFoundError:
        return HttpResponse('Service worker not found', status=404)


@require_http_methods(["GET"])
@cache_control(max_age=3600)
def manifest(request):
    """Serve manifest.json from root path"""
    manifest_path = os.path.join(settings.BASE_DIR, 'seoto', 'static', 'manifest.json')
    try:
        with open(manifest_path, 'r') as f:
            manifest_content = f.read()
        return HttpResponse(manifest_content, content_type='application/manifest+json')
    except FileNotFoundError:
        return HttpResponse('Manifest not found', status=404)


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

    # Workaround for py-vapid: save private key to temp file
    # py-vapid 1.9.1 doesn't support loading PEM from string
    # Also normalize escaped newlines (\n) that env vars on PythonAnywhere may store as literals
    import tempfile
    pem_key = settings.VAPID_PRIVATE_KEY.replace('\\n', '\n')
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as f:
        f.write(pem_key)
        vapid_key_path = f.name

    try:
        # Send to all subscriptions
        success_count = 0
        payload_json = json.dumps(payload)
        logger.info(f"Sending push notification with payload: {payload_json}")

        for subscription in subscriptions:
            try:
                logger.info(f"Sending to endpoint: {subscription.endpoint[:50]}...")
                webpush(
                    subscription_info=subscription.get_subscription_info(),
                    data=payload_json,
                    vapid_private_key=vapid_key_path,  # Pass file path instead of string
                    vapid_claims={
                        "sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"
                    }
                )
                logger.info(f"Push sent successfully to {subscription.endpoint[:50]}...")
                success_count += 1
            except WebPushException as e:
                logger.exception(f"Push failed for {subscription.endpoint}")
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
    finally:
        # Clean up temp file
        try:
            os.unlink(vapid_key_path)
        except:
            pass
