from django.urls import path
from foodie import views

urlpatterns = [
	path('', views.foodie, name='foodie'),
	path('REST', views.foodie_rest, name='foodie_rest'),
	path('ALL', views.all_foodie_rest, name='all_foodie_rest'),
	path('config', views.foodie_config, name='foodie_config'),
	path('config/<str:mealtime>', views.foodie_config, name='foodie_config_time'),
]