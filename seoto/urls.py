from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from foodie.views import foodie
from interest_calc.views import interest
from rhymes.views import rhymes
from throw_a_die.views import die
from flip_a_coin.views import coin

from home.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),

    path('', index, name='index'),

    path('foodie', foodie, name='foodie'),
    path('interest_calculator', interest, name='interest_calculator'),
    path('rhymes', rhymes, name='rhymes'),
    path('throw_a_die', die, name='throw_a_die'),
    path('flip_a_coin', coin, name='flip_a_coin')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

