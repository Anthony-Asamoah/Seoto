import re
from urllib.parse import urlsplit

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render

# Fields we refuse to echo back into the retry page's HTML — the page would put them
# in the DOM, in view-source and in the bfcache copy of the page.
SENSITIVE_FIELD_RE = re.compile(r'pass|secret|token|otp|cvv|card|pin\b', re.IGNORECASE)

FORM_CONTENT_TYPES = ('application/x-www-form-urlencoded', 'multipart/form-data')

# Enough for any form in the app; keeps a huge POST from being rebuilt into a huge page.
MAX_RETRY_FIELDS = 100
MAX_RETRY_PAYLOAD_CHARS = 100_000


def error404(request, *args, **kwargs):
    return render(request, 'Home/404.html', status=404)


def error500(request, *args, **kwargs):
    return render(request, 'Home/500.html', status=500)


def _wants_json(request):
    accept = request.META.get('HTTP_ACCEPT', '')
    return (
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        or 'application/json' in accept
        or request.content_type == 'application/json'
    )


def _is_same_origin(request):
    """
    True when the browser says the POST came from one of our own pages.

    A failed CSRF check can mean the token went stale (our problem, worth offering a
    retry for) or that another site posted to us (an attack — offering the user a
    'Try again' button would just be asking them to complete it by hand).
    """
    source = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_REFERER')
    if not source:
        return False
    return urlsplit(source).netloc == request.get_host()


def _retry_fields(request):
    """
    Rebuild the submitted form as (name, value) pairs so the retry page can re-post it.

    Returns (replayable, fields, dropped_names). `replayable` is False when the post
    can't be faithfully rebuilt — file uploads can't be re-attached from HTML, and an
    oversized post isn't worth turning into a page — in which case offering a retry
    button would silently submit something other than what the user filled in.
    """
    form_encoded = request.content_type in FORM_CONTENT_TYPES
    if request.FILES or not form_encoded:
        return False, [], []

    fields, dropped, size = [], [], 0
    for name in request.POST:
        if name == 'csrfmiddlewaretoken':
            continue
        if SENSITIVE_FIELD_RE.search(name):
            dropped.append(name)
            continue
        for value in request.POST.getlist(name):
            size += len(name) + len(value)
            if len(fields) >= MAX_RETRY_FIELDS or size > MAX_RETRY_PAYLOAD_CHARS:
                return False, [], []
            fields.append((name, value))

    return True, fields, dropped


def csrf_failure(request, reason=''):
    """
    Friendly replacement for Django's bare 'CSRF verification failed' page.

    Issues a fresh CSRF cookie and, for a same-origin post, offers to re-submit what
    the user just typed. The retry still needs an explicit click on our own page, so
    the request stays user-initiated — an automatic resubmit would defeat the check.
    """
    get_token(request)  # CsrfViewMiddleware.process_response sets the refreshed cookie

    if _wants_json(request):
        return JsonResponse(
            {
                'error': 'csrf_failure',
                'detail': 'Your security token expired. Retry with a fresh token.',
                'reason': reason,
            },
            status=403,
        )

    can_retry, fields, dropped = False, [], []
    if _is_same_origin(request):
        can_retry, fields, dropped = _retry_fields(request)

    query = request.META.get('QUERY_STRING', '')
    return render(
        request,
        'Home/403_csrf.html',
        {
            'can_retry': can_retry,
            'retry_action': f'{request.path}?{query}' if query else request.path,
            'retry_fields': fields,
            'dropped_fields': dropped,
        },
        status=403,
    )
