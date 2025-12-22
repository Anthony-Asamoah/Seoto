from django.urls import path
from .consumers import FoodieConsumer

websocket_urlpatterns = [
    path("ws/foodie/", FoodieConsumer.as_asgi()),
]
