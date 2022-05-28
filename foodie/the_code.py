from .models import meal

from random import randint
from datetime import datetime


def suggest():
	hour = datetime.now().hour

	available = ['Some Water', 'Tea', 'A Beverage']
	mealtime = 'Fasting'

	fancy = meal.objects.filter(isFancy=True)

	if hour in range(6, 10):
		mealtime = 'Breakfast'
		available = meal.objects.filter(isBreakfast=True)

	if hour in range(10, 13):
		mealtime = 'Brunch'
		available = meal.objects.filter(isBrunch=True)

	if hour in range(13, 18):
		mealtime = 'Lunch'
		available = meal.objects.filter(isLunch=True)

	if hour in range(18, 21):
		mealtime = 'Dinner'
		available = meal.objects.filter(isDinner=True)

	if hour in range(21, 24):
		mealtime = 'Extra'
		available = meal.objects.filter(isExtra=True)

	if available:
		suggestion1 = available[randint(0, len(available) - 1)]
		suggestion2 = available[randint(0, len(available) - 1)]

		if fancy:
			fancy = fancy[randint(0, len(fancy) - 1)]
		# To ensure both suggestions are not the same
		while suggestion2 == suggestion1:
			suggestion2 = available[randint(0, len(available) - 1)]

		return {
			'mealtime': mealtime,
			'option1': suggestion1,
			'option2': suggestion2,
			'fancy': fancy
		}

	else:
		return {
			'mealtime': mealtime,
			'option1': None,
			'option2': None,
			'fancy': None
		}
