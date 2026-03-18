from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=get_user_model())
def create_user_meal_schedule(sender, instance, created, **kwargs):
    """On new user: seed UserMealSchedule entries and userPreference menu from meal categories."""
    if not created:
        return
    try:
        from .models import MealTimeSlot, UserMealSchedule, meal, userPreference

        slot_map = {s.label: s for s in MealTimeSlot.objects.all()}

        # Seed schedule (exclude fancy pseudo-slot)
        for label, slot in slot_map.items():
            if label == 'fancy': continue

            UserMealSchedule.objects.get_or_create(
                user=instance,
                slot_id=slot.label,
                defaults={'time': slot.default_time}
            )

        # Seed menu preferences from each system meal's categories list
        for m in meal.objects.filter(is_public=True, created_by=None):
            for label in (m.categories or []):
                slot = slot_map.get(label)
                if not slot: continue
                userPreference.objects.get_or_create(
                    user=instance,
                    meal=m,
                    slot_id=slot.label,
                    defaults={'isAvailable': True}
                )
    except Exception as e:
        import sys
        from home.services import ErrorLogService
        ErrorLogService.log(
            message=f"Failed to seed meal schedule/preferences for user {instance.pk}: {e}",
            logger_name=__name__,
            exc_info=sys.exc_info(),
        )
