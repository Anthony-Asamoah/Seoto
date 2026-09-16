import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

from domains.home.utils import get_client_ip

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """Rate limit POST requests to auth endpoints using Django's cache framework."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = getattr(settings, 'RATE_LIMIT_CONFIG', {
            '/accounts/login/': {'max_requests': 5, 'window': 300},
            '/accounts/register': {'max_requests': 5, 'window': 300},
            '/accounts/password_reset/': {'max_requests': 3, 'window': 300},
        })

    def __call__(self, request):
        if request.method != 'POST':
            return self.get_response(request)

        path = request.path
        limit_config = self.rate_limits.get(path)

        if limit_config is None:
            return self.get_response(request)

        ip = get_client_ip(request)
        cache_key = f"rate_limit:{path}:{ip}"
        max_requests = limit_config['max_requests']
        window = limit_config['window']

        request_count = cache.get(cache_key, 0)

        if request_count >= max_requests:
            logger.warning("Rate limit exceeded for %s on %s", ip, path)
            return HttpResponse("Too many requests. Please try again later.", status=429)

        cache.set(cache_key, request_count + 1, window)
        return self.get_response(request)
