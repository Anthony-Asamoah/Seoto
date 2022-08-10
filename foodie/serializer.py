from django.contrib.sites.shortcuts import get_current_site
from seoto.settings import MEDIA_URL
from foodie.models import meal
import logging


def append_host_url(queryset, url):
	for i in queryset.keys():
		if 'img' in i:
			queryset.update({i: f'{url}/{MEDIA_URL}{queryset[i]}'})
	return queryset


def serialize_mealtime(context, request):
	result = {}
	url = get_current_site(request)

	mealtime = context['mealtime']
	result.update(dict(mealtime=mealtime))

	one = context['option_1']
	one = meal.objects.all().filter(name=one.name).values()[0]
	result.update(dict(option_1=append_host_url(one, url)))

	two = context['option_2']
	two = meal.objects.all().filter(name=two.name).values()[0]
	result.update(dict(option_2=append_host_url(two, url)))

	if 'fancy' in context.keys():
		fancy = context['fancy']
		fancy = meal.objects.all().filter(name=fancy.name).values()[0]
		result.update(dict(fancy=append_host_url(fancy, url)))

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