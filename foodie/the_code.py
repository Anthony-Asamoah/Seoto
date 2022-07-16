from .models import meal
import logging
from random import randint
from datetime import datetime


def suggest():
	hour = datetime.now().hour

	available = ['Some Water', 'Tea', 'A Beverage']
	mealtime = 'Fasting'

	fancy = meal.objects.filter(isAvailable=True, isFancy=True)

	if hour in range(6, 10):
		mealtime = 'Breakfast'
		available = meal.objects.filter(isAvailable=True, isBreakfast=True)

	if hour in range(10, 13):
		mealtime = 'Brunch'
		available = meal.objects.filter(isAvailable=True, isBrunch=True)

	if hour in range(13, 18):
		mealtime = 'Lunch'
		available = meal.objects.filter(isAvailable=True, isLunch=True)

	if hour in range(18, 21):
		mealtime = 'Dinner'
		available = meal.objects.filter(isAvailable=True, isDinner=True)

	if hour in range(21, 24):
		mealtime = 'Extra'
		available = meal.objects.filter(isAvailable=True, isExtra=True)

	if available:
		suggestion1 = available[randint(0, len(available) - 1)]
		suggestion2 = available[randint(0, len(available) - 1)]

		# To ensure both suggestions are not the same
		if len(available) > 1:
			print('checking suggestion2')
			while suggestion2 == suggestion1:
				suggestion2 = available[randint(0, len(available) - 1)]

		context = {
			'mealtime': mealtime,
			'option_1': suggestion1,
			'option_2': suggestion2,
		}

		if fancy:
			fancy = fancy[randint(0, len(fancy) - 1)]
			context.update({'fancy': fancy})

	return context
