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
