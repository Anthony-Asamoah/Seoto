import re

from django.http import HttpResponseNotFound

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
