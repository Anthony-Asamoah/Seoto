from django.urls import path

from home.views import Dashboard, incoming

urlpatterns = [
    path('dashboard/', Dashboard.as_view(), name='dashboard'),
    path('incoming', incoming, name='incoming'),
]
