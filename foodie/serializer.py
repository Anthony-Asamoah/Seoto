from django.contrib.sites.shortcuts import get_current_site
from seoto.settings import MEDIA_URL
from foodie.models import meal
import logging


def serialize(context, request):
	result = {}
	url = get_current_site(request)

	def include_img_url(queryset):
		for i in queryset.keys():
			if 'img' in i:
				queryset.update({i: f'{url}/{MEDIA_URL}{queryset[i]}'})
		return queryset

	mealtime = context['mealtime']
	result.update(dict(mealtime=mealtime))

	one = context['option_1']
	one = meal.objects.all().filter(name=one.name).values('id', 'name', 'main_img', 'img_1', 'img_2', 'img_3')[0]
	result.update(dict(option_1=include_img_url(one)))

	two = context['option_2']
	two = meal.objects.all().filter(name=two.name).values('id', 'name', 'main_img', 'img_1', 'img_2', 'img_3')[0]
	result.update(dict(option_2=include_img_url(two)))

	if 'fancy' in context.keys():
		fancy = context['fancy']
		fancy = meal.objects.all().filter(name=fancy.name).values('id', 'name', 'main_img', 'img_1', 'img_2', 'img_3')[0]
		result.update(dict(fancy=include_img_url(fancy)))

	logging.info(result)

	return result
