from django.conf import settings
from django.db import models


class meal(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    nutrients = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    cooking_duration = models.CharField(max_length=40, blank=True)

    main_img = models.ImageField(upload_to=f'food', blank=True)
    img_1 = models.ImageField(upload_to=f'food', blank=True)
    img_2 = models.ImageField(upload_to=f'food', blank=True)
    img_3 = models.ImageField(upload_to=f'food', blank=True)

    def __str__(self):
        return f"{self.name}"


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
