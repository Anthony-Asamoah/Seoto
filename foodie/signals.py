from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=get_user_model())
def create_user_meal_schedule(sender, instance, created, **kwargs):
    """Seed UserMealSchedule entries for every new user from current MealTimeSlot defaults."""
    if not created: return
    try:
        from .models import MealTimeSlot, UserMealSchedule
        for slot in MealTimeSlot.objects.exclude(label='fancy'):
            UserMealSchedule.objects.get_or_create(
                user=instance,
                slot=slot,
                defaults={'time': slot.default_time}
            )
    except Exception:
        pass
