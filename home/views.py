from django.shortcuts import render
from datetime import datetime


def index(request):
    today = datetime.now()

    context = {
        'year': today.year
    }
    return render(request, 'Home/index.html', context)


def error404(request, exception):
    return render(request, 'Home/404.html', status=404)


def error500(request):
    return render(request, 'Home/500.html', status=500)
