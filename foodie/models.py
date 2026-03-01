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


class meal(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    nutrients = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    cooking_duration = models.CharField(max_length=40, blank=True)

    main_img = models.ImageField(upload_to=meal_image_path, blank=True)
    img_1 = models.ImageField(upload_to=partial(meal_image_path, slot=2), blank=True)
    img_2 = models.ImageField(upload_to=partial(meal_image_path, slot=3), blank=True)
    img_3 = models.ImageField(upload_to=partial(meal_image_path, slot=4), blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_meals'
    )
    is_public = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
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

    def __str__(self):
        return f"{self.name}"


class MealOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_orders')
    details = models.TextField(blank=True, help_text='Optional details or instructions for this order')
    meal = models.ForeignKey(meal, on_delete=models.CASCADE, related_name='meal_orders')
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    location = models.CharField(max_length=100, blank=True)
    is_confirmed = models.BooleanField(default=False)
    is_purchased = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)
    not_available = models.BooleanField(default=False,
                                        help_text="If checked, this order can be edited by the user to choose alternatives.")
    date_ordered = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_ordered']

    def __str__(self):
        return f"{self.user.username} - {self.meal.name}"

    def reset_to_pending(self):
        """Clear status flags to return order to pending state."""
        self.is_confirmed = False
        self.is_purchased = False
        self.is_delivered = False
        self.not_available = False
        self.save(update_fields=[
            'is_confirmed', 'is_purchased', 'is_delivered', 'not_available'
        ])

    def clean_location(self):
        if self.location:
            self.location = self.location.strip().title()


class userPreference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_preferences')
    meal = models.ForeignKey(meal, on_delete=models.CASCADE, related_name='user_preferences')

    isBreakfast = models.BooleanField(default=False)
    isBrunch = models.BooleanField(default=False)
    isLunch = models.BooleanField(default=False)
    isDinner = models.BooleanField(default=False)
    isExtra = models.BooleanField(default=False)
    isFancy = models.BooleanField(default=False)
    isAvailable = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'meal')

    def __str__(self):
        return f"{self.user} · {self.meal}"
