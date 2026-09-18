import functools

from django.db import close_old_connections

SCHEDULED_JOBS = []


def scheduled_job(*, trigger, id, **job_kwargs):
    """Register a job.

    `trigger` is 'interval' (`seconds`/`minutes`/`hours`, anchored to local midnight) or
    'cron' (`hour` and `minute`, each an int, an iterable or '*'; minute defaults to 0).
    `misfire_grace` seconds, if given, skips a run that is already later than that.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            close_old_connections()
            try:
                return func(*args, **kwargs)
            finally:
                close_old_connections()

        SCHEDULED_JOBS.append({
            'func': wrapper,
            'trigger': trigger,
            'id': id,
            **job_kwargs,
        })
        return wrapper

    return decorator
