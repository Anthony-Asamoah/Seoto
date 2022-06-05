from django.urls import path
from .views import jotter


urlpatterns = [
	path('jotter', jotter, name='jotter'),
]