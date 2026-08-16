# music-streaming-backend/music/urls.py
from django.urls import path
from .views import (
    ArtistStatisticsView, PlaylistCreateView, PlaylistUpdateView, PlaylistDeleteView,
    AddMusicToPlaylistView, RemoveMusicFromPlaylistView,
    AlbumCreateView, MusicCreateView, MusicListView, AlbumListView,
    AlbumDetailView, MyAlbumsListView, ToggleLikeView, RecordStreamView,
    MyPlaylistsListView, 
    PlaylistDetailView,
    UnifiedSearchView,MyMusicsListView,
    MusicDetailUpdateDeleteView,AlbumDetailUpdateDeleteView
)

urlpatterns = [
    # اندپوینت‌های لایک و استریم
    path('musics/<int:pk>/like/', ToggleLikeView.as_view(), name='music-like'),
    path('musics/<int:pk>/stream/', RecordStreamView.as_view(), name='music-stream'),
    
    # اندپوینت‌های آلبوم و موزیک
    path('my-albums/', MyAlbumsListView.as_view(), name='my-albums'), 
    path('albums/<int:pk>/', AlbumDetailView.as_view(), name='album-detail'),
    path('musics/', MusicListView.as_view(), name='music-list'),
    path('albums/', AlbumListView.as_view(), name='album-list'),
    path('albums/create/', AlbumCreateView.as_view(), name='album-create'),
    path('musics/create/', MusicCreateView.as_view(), name='music-create'),
    
    # اندپوینت‌های پلی‌لیست
    path('my-playlists/', MyPlaylistsListView.as_view(), name='my-playlists'), # اضافه شدن لیست پلی‌لیست‌های کاربر
    path('playlists/', PlaylistCreateView.as_view(), name='playlist-create'),

    path('playlists/<int:pk>/', PlaylistDetailView.as_view(), name='playlist-detail'),
    
    # باگ مسیرهای تکراری با اضافه کردن /update و /delete حل شد
    path('playlists/<int:pk>/update/', PlaylistUpdateView.as_view(), name='playlist-update'),
    path('playlists/<int:pk>/delete/', PlaylistDeleteView.as_view(), name='playlist-delete'),
    
    path('playlists/<int:pk>/add-music/', AddMusicToPlaylistView.as_view(), name='playlist-add-music'),
    path('playlists/<int:pk>/remove-music/', RemoveMusicFromPlaylistView.as_view(), name='playlist-remove-music'),

    path('search/', UnifiedSearchView.as_view(), name='unified-search'),

    path('artists/<int:artist_id>/statistics/', ArtistStatisticsView.as_view(), name='artist-statistics'),
    path('my-musics/', MyMusicsListView.as_view(), name='my-musics-list'),
    path('musics/<int:pk>/delete/', MusicDetailUpdateDeleteView.as_view(), name='music-delete'),
    path('musics/<int:pk>/edit/', MusicDetailUpdateDeleteView.as_view(), name='music-edit'),
    path('albums/<int:pk>/delete/', AlbumDetailUpdateDeleteView.as_view(), name='album-delete'),
    path('albums/<int:pk>/edit/', AlbumDetailUpdateDeleteView.as_view(), name='album-edit'),
]