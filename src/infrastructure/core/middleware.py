import logging
import re

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound

from domains.home.utils import get_client_ip

logger = logging.getLogger(__name__)

# Patterns that indicate bot/scanner probes
SCANNER_PATTERNS = re.compile(
    r'^/('
    r'wp-[\w-]+|'           # WordPress paths: wp-login.php, wp-admin, wp-content, etc.
    r'xmlrpc\.php|'
    r'\.well-known/|'
    r'\.env|'
    r'cgi-bin/|'
    r'\.git/|'
    r'\.svn/|'
    r'vendor/|'
    r'node_modules/'
    r')',
    re.IGNORECASE
)

SCANNER_EXTENSIONS = re.compile(
    r'\.(php|asp|aspx|jsp|cgi)$',
    re.IGNORECASE
)


class BotScannerMiddleware:
    """Return early 404 for common scanner/probe paths without Django logging a WARNING."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if SCANNER_PATTERNS.search(path) or SCANNER_EXTENSIONS.search(path):
            return HttpResponseNotFound()

        return self.get_response(request)


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
