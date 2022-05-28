from django.db import models


class meal(models.Model):
	isBreakfast = models.BooleanField(default=False)
	isBrunch = models.BooleanField(default=False)
	isLunch = models.BooleanField(default=False)
	isDinner = models.BooleanField(default=False)
	isExtra = models.BooleanField(default=False)
	isFancy = models.BooleanField(default=False)
	IsAvailable = models.BooleanField(default=True)

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
