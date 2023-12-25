import logging

from django.contrib import messages
from django.shortcuts import render
from django.views import View

from .the_code import Calculator, Validation


class Interest(View):
    def get(self, request):
        return render(request, 'interest/interest.html')

    def post(self, request):
        principal = request.POST['principal']
        rate = request.POST['rate']
        time = request.POST['time']
        kind = request.POST['type']
        logging.debug(f'principal: {principal, type(principal)}, rate: {rate, type(rate)}, time: {time, type(time)}')

        context = {'principal': principal, 'rate': rate, 'time': time}
        try:
            Validation.is_valid(principal, rate, time, kind)
            context['result'] = Calculator(principal, rate, time).calculate(kind)
            return render(request, 'interest/interest.html', context)

        except ValueError as e:
            messages.error(request, str(e))
            context.update({'error': True})
            return render(request, 'interest/interest.html', context)
