"""
Standalone PythonAnywhere scheduled task script for sending meal notification push alerts.

Run hourly via PythonAnywhere Scheduled Tasks:
    python /home/Tony48/tony48.pythonanywhere.com/scripts/send_meal_notifications_pa.py
"""
import sys
import os

PROJECT_ROOT = '/home/Tony48/tony48.pythonanywhere.com'
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seoto.settings')

# --- debug ---
print(f'[debug] CWD: {os.getcwd()}')
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
print(f'[debug] .env path: {dotenv_path}')
print(f'[debug] .env exists: {os.path.exists(dotenv_path)}')
print(f'[debug] LOG_LEVEL in env before setup: {os.environ.get("LOG_LEVEL")}')
# --- end debug ---

import django
django.setup()

from datetime import datetime

from foodie.models import UserMealSchedule
from foodie.services import suggest
from pwa.models import PushSubscription
from pwa.services import send_push_notification


def run():
    current_hour = datetime.now().hour

    due_schedules = UserMealSchedule.objects.select_related('user', 'slot').filter(
        time__hour=current_hour,
    )

    if not due_schedules.exists():
        print(f'No meal times scheduled for hour {current_hour:02d}:xx.')
        return

    sent_count = 0
    skipped_count = 0
    seen_users = set()

    for schedule in due_schedules:
        user = schedule.user

        if user.id in seen_users:
            continue
        seen_users.add(user.id)

        if not PushSubscription.objects.filter(user=user, is_active=True).exists():
            skipped_count += 1
            continue

        context = suggest(user)
        if not context.get('option_1'):
            skipped_count += 1
            continue

        option_1 = context['option_1']
        option_2 = context.get('option_2')
        mealtime = context.get('mealtime', schedule.slot.label)

        title = f"Time for {mealtime.capitalize()}!"
        if option_2 and option_2['name'] != option_1['name']:
            body = f"How about {option_1['name']} or {option_2['name']}?"
        else:
            body = f"How about {option_1['name']}?"

        result = send_push_notification(
            user=user,
            title=title,
            body=body,
            url='/foodie/',
        )

        if result:
            sent_count += 1
            print(f'  Sent to {user.username}: "{title}" — {body}')
        else:
            skipped_count += 1

    print(f'\nDone. Sent: {sent_count}, Skipped: {skipped_count}.')


if __name__ == '__main__':
    run()
