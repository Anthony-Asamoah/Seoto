from datetime import datetime


def _at(hour, minute=0):
    """Build a datetime for today at the given wall-clock time."""
    return datetime(2026, 5, 3, hour, minute)
