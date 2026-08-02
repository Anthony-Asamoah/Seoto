from random import randint

from django.shortcuts import render
from django.views import View


class Coin(View):
    def post(self, request):
        text = {1: 'Heads', 2: 'Tails'}
        flip = randint(1, 2)
        return render(request, 'flip_a_coin/coin.html', {'text': text.get(flip), 'flip': flip})

    def get(self, request):
        return render(request, 'flip_a_coin/coin.html')
