"""OpenAPI schema and Swagger UI for the public API.

Only mounted when ``IS_API_DOCS_ENABLED`` is on — see ``core/urls.py``, which
gates this the same way it gates the theme app.
"""
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
]
