import functools
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=3)


def heartbeat(func):
    """Record that the sweeper ran, so the admin can show whether beat and the worker are alive."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            try:
                cache.set(f'heartbeat:{func.__name__}', timezone.now(), None)
            except Exception:
                logger.warning('Could not record heartbeat for %s', func.__name__, exc_info=True)

    return wrapper


def sweeper_status():
    now = timezone.now()
    rows = []
    for entry in settings.CELERY_BEAT_SCHEDULE.values():
        name = entry['task'].rsplit('.', 1)[1]
        last = cache.get(f'heartbeat:{name}')
        rows.append({'name': name, 'last_run': last, 'stale': last is None or now - last > STALE_AFTER})
    return rows
