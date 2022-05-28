from django.shortcuts import render, HttpResponse
from .the_code import interest as calc


def interest(request):
	if request.method == 'POST':
		principal = request.POST['principal']
		rate = request.POST['rate']
		time = request.POST['time']
		kind = request.POST['type']

		context = {
			'principal': principal,
			'rate': rate,
			'time': time,
			'kind': kind,
		}

		if principal and rate and time:
			raw_data = calc(principal, rate, time)
			amount = raw_data.simple()

			if kind == 'compound':
				amount = raw_data.compound()
			if kind == 'cumulative':
				amount = raw_data.susu()

			context.update({'amount': amount})
		else:
			context.update({'amount': "Kindly fill in all inputs with numbers"})

		return render(request, 'interest/interest.html', context)

	return render(request, 'interest/interest.html')
