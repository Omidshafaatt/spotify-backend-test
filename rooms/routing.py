# rooms/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/rooms/(?P<uuid>[0-9a-f-]+)/$', consumers.RoomConsumer.as_asgi()),
]