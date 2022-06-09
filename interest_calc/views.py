from django.shortcuts import render, HttpResponse
import logging

from .the_code import interest as calc, validation


def interest(request):
	if request.method == 'POST':
		principal = request.POST['principal']
		rate = request.POST['rate']
		time = request.POST['time']
		kind = request.POST['type']
		logging.info(f'principal: {principal, type(principal)}, rate: {rate, type(rate)}, time: {time, type(time)}')

		context = {
			'principal': principal,
			'rate': rate,
			'time': time,
			'kind': kind,
		}

		if principal and rate and time:
			isValid = validation(principal, rate, time)
		else:
			isValid = False

		if isValid:
			raw_data = calc(principal, rate, time)
			amount = raw_data.simple()

			if kind == 'compound':
				amount = raw_data.compound()
			if kind == 'cumulative':
				amount = raw_data.susu()

			context.update({'amount': amount})
		else:
			context.update({'amount': "Kindly fill in all inputs with positive numbers only"})

		return render(request, 'interest/interest.html', context)

	return render(request, 'interest/interest.html')
