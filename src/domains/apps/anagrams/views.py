import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from domains.apps.anagrams.the_code import AnagramSolver
from infrastructure.core.exceptions import InvalidInput


class Anagrams(View):
    def get(self, request):
        return render(request, 'anagrams/anagrams.html')

    @method_decorator(never_cache)
    def post(self, request):
        letters = request.POST.get('letters', '')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        context = {'input': letters, 'exact': None, 'groups': None, 'amount': None}
        error = None
        try:
            solver = AnagramSolver(letters)
            context['input'] = solver.letters
            context['exact'] = solver.get_exact()
            context['groups'] = solver.get_groups()
            context['amount'] = solver.word_count()
        except InvalidInput as e:
            error = str(e)
        except Exception:
            logging.exception("Error while solving anagram")
            error = "Something went wrong"

        if is_ajax:
            if error:
                return JsonResponse({'error': error}, status=400)
            return JsonResponse({
                'input': context['input'],
                'exact': context['exact'] or [],
                'groups': context['groups'] or [],
                'amount': context['amount'] or 0,
            })

        if error:
            messages.error(request, error)
        return render(request, 'anagrams/anagrams.html', context)
