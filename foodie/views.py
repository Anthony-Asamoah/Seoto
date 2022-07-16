from django.http import JsonResponse
from django.shortcuts import render
from .serializer import serialize

from . import the_code


def foodie(request):
	context = the_code.suggest()
	return render(request, 'foodie/foodie.html', context)


def foodie_rest(request):
	context = the_code.suggest()
	context = serialize(context)

	return JsonResponse(context)

