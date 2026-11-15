from celery import shared_task

from common.heartbeat import heartbeat

from .services import send_due_meal_notifications


@shared_task
@heartbeat
def send_meal_notifications():
    return send_due_meal_notifications()
