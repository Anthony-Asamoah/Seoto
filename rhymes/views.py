import logging
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from rhymes.models import Rhyme
from rhymes.the_code import RhymeDB
from seoto.exceptions import InvalidInput


class Rhymes(View):
    def get(self, request):
        return render(request, 'rhymes/rhymes.html')

    @method_decorator(never_cache)
    def post(self, request):
        rhyme = request.POST.get('rhyme', '')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        context = {
            'input': rhyme,
            'words': None,
            'amount': None
        }
        error = None
        try:
            helper = RhymeDB(rhyme)
            context['words'] = helper.get_all_words()
            context['amount'] = helper.word_count()
            if request.user.is_authenticated and not helper.is_empty():
                user: User = request.user
                Rhyme.create(user=user, rhyme=rhyme, text=helper.get_text(), word_count=helper.word_count())
        except InvalidInput as e:
            error = str(e)
        except ValidationError as e:
            error = ', '.join(e.messages)
        except Exception:
            logging.exception("Error while generating rhyme")
            error = "Something went wrong"

        if is_ajax:
            if error:
                return JsonResponse({'error': error}, status=400)
            return JsonResponse({
                'input': rhyme,
                'words': context['words'] or [],
                'amount': context['amount'] or 0,
                'can_download': request.user.is_authenticated and bool(context['words']),
            })

        if error:
            messages.error(request, error)
        return render(request, 'rhymes/rhymes.html', context)

    @staticmethod
    @login_required
    @csrf_protect
    def download(request):
        # Only allow POST requests for security
        if request.method != 'POST':
            messages.error(request, 'Invalid request method')
            return redirect('rhymes')

        user: User = request.user

        # Get the user's Rhyme record from database
        try:
            rhyme_obj = Rhyme.objects.get(user=user)
        except Rhyme.DoesNotExist:
            messages.error(request, 'No rhyme data available. Please generate a rhyme first.')
            return redirect('rhymes')

        # Generate file content on-the-fly
        file_content = rhyme_obj.generate_file_content()

        # Create in-memory file buffer
        buffer = BytesIO()
        buffer.write(file_content.encode('utf-8'))
        buffer.seek(0)

        # Return as downloadable file
        filename = f'{user.email}-rhymes.txt'
        return FileResponse(buffer, as_attachment=True, filename=filename)
