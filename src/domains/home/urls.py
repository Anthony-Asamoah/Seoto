from django.urls import path

from domains.home.views import (
    Home,
    app_usage,
    dashboard,
    errors_list,
    incoming,
    message_detail,
    messages_list,
    user_analytics,
    weather_forecast,
    weather_search,
)

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/errors/', errors_list, name='dashboard_errors'),
    path('dashboard/users/', user_analytics, name='dashboard_users'),
    path('dashboard/usage/', app_usage, name='dashboard_usage'),
    path('dashboard/messages/', messages_list, name='dashboard_messages'),
    path('dashboard/messages/<int:pk>/', message_detail, name='message_detail'),
    path('incoming', incoming, name='incoming'),
    path('weather/forecast/', weather_forecast, name='weather_forecast'),
    path('weather/search/', weather_search, name='weather_search'),
]
