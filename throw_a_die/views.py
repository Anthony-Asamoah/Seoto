from django.shortcuts import render
from random import randint


def die(request):
	if request.method == 'POST':
		return render(request, 'throw_a_die/die.html', {'side': randint(1, 6)})

	return render(request, 'throw_a_die/die.html', {'side': None})
