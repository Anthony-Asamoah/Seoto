from django.conf.urls.static import static
from django.urls import path, include
from django.contrib import admin
from django.conf import settings

from home.views import index, error404, error500

from author.views import about
from rhymes.views import rhymes, download_rhyme
from throw_a_die.views import die
from flip_a_coin.views import coin
from interest_calc.views import interest
from home.views import incoming


urlpatterns = [
    path('@sean_or_tony', about, name='about'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),

    path('', index, name='index'),
    # Anonymous User apps
    path('foodie/', include('foodie.urls')),
    path('interest_calculator', interest, name='interest_calculator'),
    path('rhymes', rhymes, name='rhymes'),
    path('rhymes/download', download_rhyme, name='rhymes_download'),
    path('throw_a_die', die, name='throw_a_die'),
    path('flip_a_coin', coin, name='flip_a_coin'),
    # Registered User apps
    path('jotter/', include('jotter.urls')),
    path('incoming', incoming, name='incoming'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = error404
handler500 = error500
