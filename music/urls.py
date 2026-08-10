# music-streaming-backend/music/urls.py
from django.urls import path
from .views import (PlaylistCreateView, PlaylistUpdateView, PlaylistDeleteView,
                    AddMusicToPlaylistView, RemoveMusicFromPlaylistView)

urlpatterns = [
    path('playlists/', PlaylistCreateView.as_view(), name='playlist-create'),
    path('playlists/<int:pk>/', PlaylistUpdateView.as_view(), name='playlist-update'),
    path('playlists/<int:pk>/', PlaylistDeleteView.as_view(), name='playlist-delete'),
    path('playlists/<int:pk>/add-music/', AddMusicToPlaylistView.as_view(), name='playlist-add-music'),
    path('playlists/<int:pk>/remove-music/', RemoveMusicFromPlaylistView.as_view(), name='playlist-remove-music'),
    
]