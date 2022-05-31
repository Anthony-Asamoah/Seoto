from django.shortcuts import render
from random import randint


def coin(request):
	if request.method == 'POST':
		flip = randint(1, 2)
		side = 'heads'

		if flip == 2:
			side = 'tails'

		context = {
			'side': side,
			'flip': flip
		}

		return render(request, 'flip_a_coin/coin.html', context)

	return render(request, 'flip_a_coin/coin.html')