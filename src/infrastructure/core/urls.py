from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from domains.author.views import About, ReachOut
from domains.apps.anagrams.views import Anagrams
from domains.apps.flip_a_coin.views import Coin
from domains.apps.generate_invoice.views import generate_invoice
from domains.home.views import (
    Apps, error404, error500
)
from domains.apps.interest_calc.views import Interest
from domains.apps.rhymes.views import Rhymes
from domains.apps.throw_a_die.views import Die

ROBOTS_TXT = """\
User-agent: *
Disallow: /admin/
Disallow: /accounts/
Allow: /
"""

urlpatterns = [
    path('robots.txt', lambda request: HttpResponse(ROBOTS_TXT, content_type='text/plain')),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('', Apps.as_view(), name='apps'),
    # path('info/', Home.as_view(), name='index'),
    path('admin/', admin.site.urls, name='admin'),
    path('api/company/', include('domains.company.urls')),
    path('accounts/', include('domains.accounts.urls')),
    path('home/', include("domains.home.urls")),
    # Anonymous
    path('reach-out', ReachOut.as_view(), name='reach_out'),
    path('foodie/', include('domains.apps.foodie.urls')),
    path('interest_calculator', Interest.as_view(), name='interest_calculator'),
    path('rhymes', Rhymes.as_view(), name='rhymes'),
    path('rhymes/download', Rhymes.download, name='rhymes_download'),
    path('anagrams', Anagrams.as_view(), name='anagrams'),
    path('throw_a_die', Die.as_view(), name='throw_a_die'),
    path('flip_a_coin', Coin.as_view(), name='flip_a_coin'),
    # Login required
    path('jotter/', include('domains.apps.jotter.urls')),
    path('blog/', include('domains.apps.blog.urls')),
    path('spending_tracker/', include('domains.apps.spending_tracker.urls')),
    path('generate_invoice/', generate_invoice, name='generate_invoice'),
    # PWA
    path('', include('domains.pwa.urls')),
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),

]

if settings.IS_THEME_ENABLED:
    urlpatterns.append(path('theme/', include('domains.theme.urls')))

if settings.IS_API_DOCS_ENABLED:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='api_schema'),
        path('api/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
    ]

if settings.MEDIA_STORAGE == 'LOCAL':
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = error404
handler500 = error500
