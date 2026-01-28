from foodie.routing import websocket_urlpatterns as foodie_ws

# Project-level WebSocket URL patterns
websocket_urlpatterns = [
    # Namespace foodie websocket endpoints
    *foodie_ws,
]
