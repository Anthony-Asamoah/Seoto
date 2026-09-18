from datetime import timedelta

MINUTES_IN_DAY = 24 * 60

INTERVAL_UNITS = {'seconds': 1, 'minutes': 60, 'hours': 3600}


def _field_values(value, valid_range):
    if value == '*':
        return set(valid_range)
    if isinstance(value, int):
        return {value}
    return {int(v) for v in value}


def interval_period(job):
    """The timedelta between fires of an 'interval' job."""
    seconds = sum(job[unit] * factor for unit, factor in INTERVAL_UNITS.items() if unit in job)
    if seconds <= 0:
        raise ValueError(f"Job {job['id']!r} needs a positive seconds/minutes/hours interval")
    return timedelta(seconds=seconds)


def _next_interval_fire(job, after):
    """Interval fires are anchored to local midnight, so they land on predictable clock times.

    A period that does not divide the day evenly restarts at midnight rather than drifting,
    which shortens that one gap.
    """
    period = interval_period(job)
    midnight = after.replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight = midnight + timedelta(days=1)

    elapsed = after - midnight
    candidate = midnight + (elapsed // period + 1) * period
    return candidate if candidate < next_midnight else next_midnight


def _next_cron_fire(job, after):
    hours = _field_values(job.get('hour', '*'), range(24))
    minutes = _field_values(job.get('minute', 0), range(60))

    candidate = (after + timedelta(minutes=1)).replace(second=0, microsecond=0)
    for _ in range(MINUTES_IN_DAY + 1):
        if candidate.hour in hours and candidate.minute in minutes:
            return candidate
        candidate += timedelta(minutes=1)
    raise ValueError(f"Job {job['id']!r} has a cron trigger that never fires")


def next_fire_time(job, after):
    """The first time `job` fires strictly after `after`.

    Dueness is this, compared against a stored next-run time — never a match on the current
    clock — so the jobs are independent of how often the runner is invoked.
    """
    trigger = job['trigger']
    if trigger == 'interval':
        return _next_interval_fire(job, after)
    if trigger == 'cron':
        return _next_cron_fire(job, after)
    raise ValueError(f"Unknown trigger {trigger!r} on job {job['id']!r}")
