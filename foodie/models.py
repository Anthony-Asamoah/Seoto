import os
from functools import partial

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from django.utils.text import slugify

_IMG_FIELDS = ['main_img', 'img_1', 'img_2', 'img_3']


def meal_image_path(instance, filename, slot=1):
    ext = os.path.splitext(filename)[1].lower()
    if instance.created_by_id:
        slug = slugify(instance.name) or 'meal'
        return f'food/user_{instance.created_by_id}_{slug}_{slot}{ext}'
    return f'food/{filename}'


class MealTimeSlot(models.Model):
    """Global reference table of named meal time slots, seeded via seed_meal_time_slots."""
    label = models.CharField(max_length=50, primary_key=True)
    default_time = models.TimeField()

    def __str__(self):
        return self.label.capitalize()


class meal(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    nutrients = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    cooking_duration = models.CharField(max_length=40, blank=True)

    main_img = models.ImageField(upload_to=meal_image_path, blank=True)
    main_img_thumbnail = models.ImageField(upload_to='food/thumbs', blank=True)
    img_1 = models.ImageField(upload_to=partial(meal_image_path, slot=2), blank=True)
    img_2 = models.ImageField(upload_to=partial(meal_image_path, slot=3), blank=True)
    img_3 = models.ImageField(upload_to=partial(meal_image_path, slot=4), blank=True)

    SLOT_CHOICES = ['breakfast', 'lunch', 'dinner', 'supper', 'snack']

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_meals'
    )
    is_public = models.BooleanField(default=True)
    is_fancy = models.BooleanField(default=False)
    categories = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        new_main_img = isinstance(self.main_img, UploadedFile)
        first_save = not self.pk

        if self.pk and self.created_by_id:
            try:
                old = meal.objects.get(pk=self.pk)
                for field_name in _IMG_FIELDS:
                    old_file = getattr(old, field_name)
                    new_file = getattr(self, field_name)
                    if old_file and isinstance(new_file, UploadedFile):
                        old_file.delete(save=False)
            except meal.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if new_main_img or first_save:
            self._generate_thumbnail()

    def _generate_thumbnail(self):
        if not self.main_img:
            self.main_img_thumbnail.delete(save=False)
            type(self).objects.filter(pk=self.pk).update(main_img_thumbnail='')
            return

        from seoto.utils import MediaHelper

        slug = slugify(self.name) or str(self.pk)
        if self.created_by_id:
            thumb_name = f'food/thumbs/user_{self.created_by_id}_{slug}_thumb.jpg'
        else:
            thumb_name = f'food/thumbs/{slug}_thumb.jpg'

        MediaHelper.generate_thumbnail(self, 'main_img', 'main_img_thumbnail', thumb_name)

    def __str__(self):
        return f"{self.name}"


class UserMealSchedule(models.Model):
    """Per-user meal time schedule. One row per slot, seeded on user creation."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_schedule')
    slot = models.ForeignKey(MealTimeSlot, on_delete=models.CASCADE, related_name='user_schedules')
    time = models.TimeField()

    class Meta:
        unique_together = ('user', 'slot')

    def __str__(self):
        return f"{self.user.username} - {self.slot} at {self.time}"


class userPreference(models.Model):
    """User's meal preference per slot. One row per user-meal-slot combination."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_preferences')
    meal = models.ForeignKey(meal, on_delete=models.CASCADE, related_name='user_preferences')
    slot = models.ForeignKey(MealTimeSlot, on_delete=models.CASCADE, related_name='preferences')
    isAvailable = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'meal', 'slot')

    def __str__(self):
        return f"{self.user} · {self.meal} · {self.slot}"


class DailyMealSuggestion(models.Model):
    """Per-(user, date, slot) cached suggestion so reloads within a mealtime are stable
    and a meal isn't repeated across mealtimes within the same day."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_suggestions')
    date = models.DateField()
    slot = models.ForeignKey(MealTimeSlot, on_delete=models.CASCADE, related_name='daily_suggestions')
    option_1 = models.ForeignKey(meal, on_delete=models.CASCADE, related_name='+')
    option_2 = models.ForeignKey(meal, on_delete=models.CASCADE, related_name='+', null=True, blank=True)
    fancy = models.ForeignKey(meal, on_delete=models.CASCADE, related_name='+', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date', 'slot')
        indexes = [models.Index(fields=['user', 'date'])]

    def __str__(self):
        return f"{self.user} · {self.date} · {self.slot}"
