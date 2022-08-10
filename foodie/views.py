from django.http import JsonResponse
from django.shortcuts import render
from .serializer import serialize_mealtime, serialize_all
from . import the_code


def foodie(request):
	context = the_code.suggest()
	return render(request, 'foodie/foodie.html', context)


def foodie_rest(request):
	context = the_code.suggest()
	context = serialize_mealtime(context, request)

	return JsonResponse(context)


def all_foodie_rest(request):
	context = the_code.get_all()
	context = serialize_all(context, request)

	return JsonResponse(context ,safe=False)