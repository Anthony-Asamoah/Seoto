from django.urls import path
from foodie import views

urlpatterns = [
    path('', views.foodie, name='foodie'),
    path('REST', views.foodie_rest, name='foodie_rest'),
    path('ALL', views.all_foodie_rest, name='all_foodie_rest'),
    path('config', views.foodie_config, name='foodie_config'),
    path('schedule/', views.meal_schedule, name='foodie_schedule'),
    path('config/<str:mealtime>', views.foodie_config, name='foodie_config_time'),
    # User-uploaded meals
    path('my-foods/', views.my_meals, name='foodie_my_meals'),
    path('my-foods/add/', views.meal_create, name='foodie_meal_create'),
    path('my-foods/<int:pk>/edit/', views.meal_edit, name='foodie_meal_edit'),
    path('my-foods/<int:pk>/delete/', views.meal_delete, name='foodie_meal_delete'),
    path('config/<str:mealtime>/search/', views.meal_search_autocomplete, name='foodie_meal_search'),
]