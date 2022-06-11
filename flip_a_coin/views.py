from django.shortcuts import render
from random import randint


def coin(request):
	if request.method == 'POST':
		flip = randint(1, 2)
		text = 'Heads'

		if flip == 2:
			text = 'Tails'

		context = {
			'text': text,
			'flip': flip
		}

		return render(request, 'flip_a_coin/coin.html', context)

	return render(request, 'flip_a_coin/coin.html')
