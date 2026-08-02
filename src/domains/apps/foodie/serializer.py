from django.contrib.sites.shortcuts import get_current_site
from infrastructure.core.settings import MEDIA_URL
from domains.apps.foodie.models import meal
import logging


def append_host_url(queryset, url):
	for i in queryset.keys():
		if 'img' in i:
			queryset.update({i: f'{url}/{MEDIA_URL}{queryset[i]}'})
	return queryset


def serialize_mealtime(context, request):
	result = {}
	if not context:
		return result
	url = get_current_site(request)

	result['mealtime'] = context.get('mealtime')

	one = context.get('option_1')
	if one:
		row = meal.objects.filter(name=one['name']).values().first()
		if row:
			result['option_1'] = append_host_url(row, url)

	two = context.get('option_2')
	if two:
		row = meal.objects.filter(name=two['name']).values().first()
		if row:
			result['option_2'] = append_host_url(row, url)

	if context.get('fancy'):
		fancy = context['fancy']
		row = meal.objects.filter(name=fancy['name']).values().first()
		if row:
			result['fancy'] = append_host_url(row, url)

	logging.info(result)

	return result


def serialize_all(context, request):
	result = {}
	context = list(context)

	for i in context:
		counter = 0
		result.update({counter: append_host_url(i, get_current_site(request))})

	logging.info(result)
	return context