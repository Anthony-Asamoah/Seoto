"""
Standalone PythonAnywhere scheduled task script for sending meal notification push alerts.

Run hourly via PythonAnywhere Scheduled Tasks:
    python /home/Tony48/tony48.pythonanywhere.com/foodie/tasks/send_meal_notifications_pa.py
"""
import sys
import os

PROJECT_ROOT = '/home/Tony48/tony48.pythonanywhere.com'
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seoto.settings')

import django
django.setup()

from foodie.services import send_due_meal_notifications


def run():
    result = send_due_meal_notifications()
    print(f"Done. Sent: {result['sent']}, Skipped: {result['skipped']}.")


if __name__ == '__main__':
    run()
