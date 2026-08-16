# rooms/urls.py
from django.urls import path
from .views import (
    CreateRoomView,
    JoinRoomView,
    RoomStatusView,
    UploadSongView,
    PlayRoomView,
    PauseRoomView,
    SeekRoomView,
    LeaveRoomView,  # new import
)

urlpatterns = [
    path('rooms/', CreateRoomView.as_view(), name='create-room'),
    path('rooms/<uuid:uuid>/join/', JoinRoomView.as_view(), name='join-room'),
    path('rooms/<uuid:uuid>/status/', RoomStatusView.as_view(), name='room-status'),
    path('rooms/<uuid:uuid>/upload/', UploadSongView.as_view(), name='upload-song'),
    path('rooms/<uuid:uuid>/play/', PlayRoomView.as_view(), name='play-room'),
    path('rooms/<uuid:uuid>/pause/', PauseRoomView.as_view(), name='pause-room'),
    path('rooms/<uuid:uuid>/seek/', SeekRoomView.as_view(), name='seek-room'),
    path('rooms/<uuid:uuid>/leave/', LeaveRoomView.as_view(), name='leave-room'),
]