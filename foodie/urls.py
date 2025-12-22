from django.urls import path
from foodie import views

urlpatterns = [
    path('', views.foodie, name='foodie'),
    path('REST', views.foodie_rest, name='foodie_rest'),
    path('ALL', views.all_foodie_rest, name='all_foodie_rest'),
    path('config', views.foodie_config, name='foodie_config'),
    path('config/<str:mealtime>', views.foodie_config, name='foodie_config_time'),
    # Orders
    path('orders/', views.orders_list, name='foodie_orders'),
    path('orders/new/', views.order_create, name='foodie_order_new'),
    path('orders/<int:pk>/edit/', views.order_edit, name='foodie_order_edit'),
]