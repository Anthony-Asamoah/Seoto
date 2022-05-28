from django.shortcuts import render
from datetime import datetime


def index(request):
	today = datetime.now()

	context = {
		'year': today.year
	}
	return render(request, 'Home/index.html', context)