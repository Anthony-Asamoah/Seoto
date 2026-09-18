"""Import job modules here so @scheduled_job decorators register before the runner starts."""

from . import foodie, spending_tracker  # noqa: F401
