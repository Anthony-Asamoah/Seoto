"""
Standalone PythonAnywhere scheduled task script for sending meal notification push alerts.

Run hourly via PythonAnywhere Scheduled Tasks:
    python /home/Tony48/tony48.pythonanywhere.com/src/domains/apps/foodie/tasks/send_meal_notifications_pa.py
"""
import sys
import os

# src/ is the import root, four levels up from this file.
SRC_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, SRC_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'infrastructure.core.settings')

import django
django.setup()

from domains.apps.foodie.services import send_due_meal_notifications


def run():
    result = send_due_meal_notifications()
    print(f"Done. Sent: {result['sent']}, Skipped: {result['skipped']}.")


if __name__ == '__main__':
    run()
