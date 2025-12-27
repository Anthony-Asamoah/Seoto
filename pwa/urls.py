from django.urls import path
from . import views

app_name = 'pwa'

urlpatterns = [
    path('api/push/vapid-public-key/', views.vapid_public_key, name='vapid_public_key'),
    path('api/push/subscribe/', views.subscribe_push, name='subscribe_push'),
    path('api/push/unsubscribe/', views.unsubscribe_push, name='unsubscribe_push'),
]
