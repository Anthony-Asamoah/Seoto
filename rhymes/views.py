import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import FileResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache

from rhymes.models import Rhyme
from rhymes.the_code import RhymeDB
from seoto.exceptions import InvalidInput


class Rhymes(View):
    def get(self, request):
        return render(request, 'rhymes/rhymes.html')

    @method_decorator(never_cache)
    def post(self, request):
        rhyme = request.POST['rhyme']
        context = {
            'input': rhyme,
            'words': None,
            'amount': None
        }
        try:
            helper = RhymeDB(rhyme)
            context['words'] = helper.get_all_words()
            context['amount'] = helper.word_count()
            if request.user.is_authenticated and not helper.is_empty():
                user: User = request.user
                obj = Rhyme.create(user=user, rhyme=rhyme, text=helper.get_text(), word_count=helper.word_count())
                obj.write_to_file(filename=f"{user.email}-rhymes.txt")
                messages.success(request, 'File Saved')
        except InvalidInput as e:
            messages.error(request, str(e))
        except ValidationError as e:
            messages.error(request, ', '.join(e.messages))
        except Exception:
            logging.exception("Error while generating rhyme")
            messages.error(request, "Something went wrong")
        finally:
            return render(request, 'rhymes/rhymes.html', context)

    @staticmethod
    @login_required
    def download(request):
        user: User = request.user
        file_path = os.path.join(settings.MEDIA_ROOT, f'{user.email}-rhymes.txt')
        if not os.path.exists(file_path):
            messages.error(request, 'File Unavailable')
            return redirect('rhymes')
        return FileResponse(open(file_path, 'rb'), as_attachment=True)
