from domains.apps.foodie.services import send_due_meal_notifications
from infrastructure.scheduler import scheduled_job


@scheduled_job(
    trigger='cron',
    id='send_meal_notifications',
    hour='*',
    minute=0,
    # A meal suggestion is worthless once the hour it belongs to has passed.
    misfire_grace=30 * 60,
)
def send_meal_notifications():
    return send_due_meal_notifications()
