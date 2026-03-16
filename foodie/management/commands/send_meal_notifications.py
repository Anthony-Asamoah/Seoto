from datetime import datetime

from django.core.management.base import BaseCommand

from foodie.models import UserMealSchedule
from foodie.services import suggest
from pwa.models import PushSubscription
from pwa.services import send_push_notification


class Command(BaseCommand):
    help = (
        'Send meal suggestion push notifications to users whose scheduled meal time falls '
        'within the current hour. Run as an hourly cron job (e.g. PythonAnywhere scheduled task).'
    )

    def handle(self, *args, **options):
        current_hour = datetime.now().hour

        due_schedules = UserMealSchedule.objects.select_related('user', 'slot').filter(
            time__hour=current_hour,
        )

        if not due_schedules.exists():
            self.stdout.write(f'No meal times scheduled for hour {current_hour:02d}:xx.')
            return

        sent_count = 0
        skipped_count = 0
        seen_users = set()

        for schedule in due_schedules:
            user = schedule.user

            # Only send once per user per run even if multiple slots match the hour
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
                self.stdout.write(self.style.SUCCESS(
                    f'  Sent to {user.username}: "{title}" — {body}'
                ))
            else:
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Sent: {sent_count}, Skipped: {skipped_count}.'
        ))
