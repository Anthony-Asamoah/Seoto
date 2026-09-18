"""
Standalone entrypoint for the scheduled jobs, for hosts that invoke a script rather than
a management command.

Run hourly via PythonAnywhere Scheduled Tasks:
    python /home/Tony48/tony48.pythonanywhere.com/src/infrastructure/scheduler/run_jobs.py

Each job decides for itself whether this hour is its hour (see infrastructure/scheduler/jobs/).
"""
import os
import sys
from collections import Counter

# src/ is the import root, three levels up from this file.
SRC_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, SRC_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from infrastructure.scheduler import run_due_jobs


def run():
    results = run_due_jobs()
    for entry in results:
        print(f'  {entry["status"]:9} {entry["id"]}: {entry["result"]}')

    counts = Counter(e['status'] for e in results)
    print(f'Ran {counts["ran"]} job(s), {counts["error"]} error(s), {counts["misfired"]} misfire(s).')
    return 1 if counts['error'] else 0


if __name__ == '__main__':
    sys.exit(run())
