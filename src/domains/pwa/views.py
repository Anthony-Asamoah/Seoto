import json
import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods

from .models import PushSubscription, Notification

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    """Serve service worker from root path to allow site-wide scope"""
    sw_path = os.path.join(settings.SRC_DIR, 'static', 'js', 'sw.js')
    try:
        with open(sw_path, 'r') as f:
            sw_content = f.read()
        # Override the file's fallback TTL with the configured env value.
        sw_content = sw_content.replace(
            'const CACHE_TTL_MS = 300000;',
            f'const CACHE_TTL_MS = {settings.CLIENT_CACHE_TTL_SECONDS * 1000};',
        )
        response = HttpResponse(sw_content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        return response
    except FileNotFoundError:
        return HttpResponse('Service worker not found', status=404)


@require_http_methods(["GET"])
@cache_control(max_age=3600)
def manifest(request):
    """Serve manifest.json from root path"""
    manifest_path = os.path.join(settings.SRC_DIR, 'static', 'manifest.json')
    try:
        with open(manifest_path, 'r') as f:
            manifest_content = f.read()
        return HttpResponse(manifest_content, content_type='application/manifest+json')
    except FileNotFoundError:
        return HttpResponse('Manifest not found', status=404)


@require_http_methods(["GET"])
def vapid_public_key(request):
    """Return VAPID public key for push subscription"""
    return JsonResponse({'publicKey': settings.VAPID_PUBLIC_KEY})


@login_required
@require_http_methods(["POST"])
def subscribe_push(request):
    """Subscribe user to push notifications"""
    try:
        subscription_data = json.loads(request.body)

        endpoint = subscription_data.get('endpoint')
        keys = subscription_data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not all([endpoint, p256dh, auth]):
            return JsonResponse({'error': 'Missing subscription data'}, status=400)

        subscription, created = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh': p256dh,
                'auth': auth,
                'is_active': True
            }
        )

        return JsonResponse({'success': True, 'created': created})

    except Exception as e:
        logger.exception(f"subscribe_push failed for user {request.user.username}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def notifications_list(request):
    """Return the 10 most recent notifications for the current user."""
    try:
        qs = request.user.notifications.all()[:10]
        unread_count = request.user.notifications.filter(is_read=False).count()
        return JsonResponse({
            'unread_count': unread_count,
            'notifications': [
                {
                    'id': n.id,
                    'title': n.title,
                    'body': n.body,
                    'url': n.url or '',
                    'is_read': n.is_read,
                    'created_at': n.created_at.isoformat(),
                }
                for n in qs
            ],
        })
    except Exception:
        logger.exception("notifications_list failed for user %s", request.user.username)
        return JsonResponse({'error': 'Failed to load notifications', 'notifications': [], 'unread_count': 0}, status=500)


@login_required
@require_http_methods(["POST"])
def mark_notifications_read(request):
    """Mark all of the current user's notifications as read."""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


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
        logger.exception(f"unsubscribe_push failed for user {request.user.username}")
        return JsonResponse({'error': str(e)}, status=500)
