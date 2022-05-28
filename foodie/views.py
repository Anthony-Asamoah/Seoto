from django.shortcuts import render, HttpResponse
from . import the_code


def foodie(request):
	context = the_code.suggest()
	return render(request, 'foodie/foodie.html', context)
