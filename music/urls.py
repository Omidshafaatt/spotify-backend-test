# music-streaming-backend/music/urls.py
from django.urls import path
from .views import (PlaylistCreateView, PlaylistUpdateView, PlaylistDeleteView,
                    AddMusicToPlaylistView, RemoveMusicFromPlaylistView,
                    AlbumCreateView, MusicCreateView,MusicListView,AlbumListView,AlbumDetailView,MyAlbumsListView,ToggleLikeView,RecordStreamView)

urlpatterns = [
  # اندپوینت‌های جدید برای ساخت آلبوم و موزیک
    path('musics/<int:pk>/like/', ToggleLikeView.as_view(), name='music-like'),
    path('musics/<int:pk>/stream/', RecordStreamView.as_view(), name='music-stream'),
    path('my-albums/', MyAlbumsListView.as_view(), name='my-albums'), 
    path('albums/<int:pk>/', AlbumDetailView.as_view(), name='album-detail'),
    path('musics/', MusicListView.as_view(), name='music-list'),
    path('albums/', AlbumListView.as_view(), name='album-list'),
    path('albums/create/', AlbumCreateView.as_view(), name='album-create'),
    path('musics/create/', MusicCreateView.as_view(), name='music-create'),
    path('playlists/', PlaylistCreateView.as_view(), name='playlist-create'),
    path('playlists/<int:pk>/', PlaylistUpdateView.as_view(), name='playlist-update'),
    path('playlists/<int:pk>/', PlaylistDeleteView.as_view(), name='playlist-delete'),
    path('playlists/<int:pk>/add-music/', AddMusicToPlaylistView.as_view(), name='playlist-add-music'),
    path('playlists/<int:pk>/remove-music/', RemoveMusicFromPlaylistView.as_view(), name='playlist-remove-music'),
    
]