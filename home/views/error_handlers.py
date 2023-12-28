from django.shortcuts import render


def error404(request, *args, **kwargs):
    return render(request, 'Home/404.html', status=404)


def error500(request, *args, **kwargs):
    return render(request, 'Home/500.html', status=500)
