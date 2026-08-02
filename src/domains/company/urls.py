"""Company API routes — mounted at /api/company/ by infrastructure.core.urls.

Each subdomain of company/ owns its own urls.py and is included from here, so
adding one never touches the root URLconf.
"""
from django.urls import include, path

urlpatterns = [
    path('products/', include('domains.company.products.urls')),
]
