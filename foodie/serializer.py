from foodie.models import meal
import logging


def serialize(context):
	result = {}

	mealtime = context['mealtime']
	result.update(dict(mealtime=mealtime))

	one = context['option_1']
	one = meal.objects.all().filter(name=one.name).values()[0]
	result.update(dict(option_1=one))

	two = context['option_2']
	two = meal.objects.all().filter(name=two.name).values()[0]
	result.update(dict(option_2=two))

	if 'fancy' in context.keys():
		fancy = context['fancy']
		fancy = meal.objects.all().filter(name=fancy.name).values()[0]
		result.update(dict(fancy=fancy))

	logging.info(result)

	return result
