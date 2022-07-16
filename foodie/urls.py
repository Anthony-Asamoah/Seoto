from django.urls import path
from foodie import views

urlpatterns = [
	path('', views.foodie, name='foodie'),
	path('REST', views.foodie_rest, name='foodie_rest')
]