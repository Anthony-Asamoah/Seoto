from random import randint

from django.shortcuts import render
from django.views import View


class Die(View):
    def post(self, request):
        return render(request, 'throw_a_die/die.html', {'side': randint(1, 6)})

    def get(self, request):
        return render(request, 'throw_a_die/die.html', {'side': None})
