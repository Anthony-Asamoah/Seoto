from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.views.generic import TemplateView

from author.views import About
from flip_a_coin.views import Coin
from home.views import (
    Home, error404, error500
)
from interest_calc.views import Interest
from rhymes.views import Rhymes
from throw_a_die.views import Die

ROBOTS_TXT = """\
User-agent: *
Disallow: /admin/
Disallow: /accounts/
Allow: /
"""

urlpatterns = [
      path('robots.txt', lambda request: HttpResponse(ROBOTS_TXT, content_type='text/plain')),
      path('', Home.as_view(), name='index'),
      path('admin/', admin.site.urls, name='admin'),
      path('accounts/', include('accounts.urls')),
      path('home/', include("home.urls")),
      # Anonymous
      path('@sean_or_tony', About.as_view(), name='about'),
      path('foodie/', include('foodie.urls')),
      path('interest_calculator', Interest.as_view(), name='interest_calculator'),
      path('rhymes', Rhymes.as_view(), name='rhymes'),
      path('rhymes/download', Rhymes.download, name='rhymes_download'),
      path('throw_a_die', Die.as_view(), name='throw_a_die'),
      path('flip_a_coin', Coin.as_view(), name='flip_a_coin'),
      # Login required
      path('jotter/', include('jotter.urls')),
      path('blog/', include('blog.urls')),
      path('spending_tracker/', include('spending_tracker.urls')),
      # PWA
      path('', include('pwa.urls')),
      path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),

  ]

# Only include theme URLs if feature is enabled
if settings.IS_THEME_ENABLED:
    urlpatterns.append(path('theme/', include('theme.urls')))

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = error404
handler500 = error500
