# music-streaming-backend/music/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Playlist,Music, Album
from .serializers import PlaylistSerializer, PlaylistCreateSerializer, AddRemoveMusicSerializer
from .permissions import IsListenerOrArtist
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import AlbumCreateSerializer, MusicCreateSerializer
from .permissions import IsArtist
from rest_framework.permissions import AllowAny
from .serializers import MusicSerializer, AlbumWithMusicsSerializer



class PlaylistCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = PlaylistCreateSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PlaylistUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = PlaylistSerializer
    # Only allow updating 'name' (partial updates)
    http_method_names = ['patch', 'put']

    def get_queryset(self):
        # Ensure user can only update their own playlists
        return Playlist.objects.filter(owner=self.request.user)


class PlaylistDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = PlaylistSerializer 
    # Only allow deleting own playlists
    def get_queryset(self):
        return Playlist.objects.filter(owner=self.request.user)

class AddMusicToPlaylistView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = AddRemoveMusicSerializer

    def get_playlist(self, pk):
        try:
            playlist = Playlist.objects.get(pk=pk, owner=self.request.user)
            return playlist
        except Playlist.DoesNotExist:
            return None

    def post(self, request, pk, *args, **kwargs):
        playlist = self.get_playlist(pk)
        if playlist is None:
            return Response(
                {"detail": "Playlist not found or you don't own it."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        music = serializer.validated_data['music_id']

        # Check if music already in playlist
        if PlaylistMusic.objects.filter(playlist=playlist, music=music).exists():
            return Response(
                {"detail": "This music is already in the playlist."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get max position and add at the end
        max_position = PlaylistMusic.objects.filter(playlist=playlist).aggregate(Max('position'))['position__max']
        position = (max_position or 0) + 1

        PlaylistMusic.objects.create(
            playlist=playlist,
            music=music,
            position=position
        )

        return Response(
            {"detail": f"Music '{music.title}' added to playlist '{playlist.name}'."},
            status=status.HTTP_201_CREATED
        )


class RemoveMusicFromPlaylistView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = AddRemoveMusicSerializer

    def get_playlist(self, pk):
        try:
            playlist = Playlist.objects.get(pk=pk, owner=self.request.user)
            return playlist
        except Playlist.DoesNotExist:
            return None

    def delete(self, request, pk, *args, **kwargs):
        playlist = self.get_playlist(pk)
        if playlist is None:
            return Response(
                {"detail": "Playlist not found or you don't own it."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        music = serializer.validated_data['music_id']

        # Check if music exists in this playlist
        try:
            playlist_music = PlaylistMusic.objects.get(playlist=playlist, music=music)
        except PlaylistMusic.DoesNotExist:
            return Response(
                {"detail": "This music is not in the playlist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete the entry (this automatically reorders positions? No, we may leave gaps.
        # Optionally we could reorder, but not required.)
        playlist_music.delete()

        return Response(
            {"detail": f"Music '{music.title}' removed from playlist '{playlist.name}'."},
            status=status.HTTP_204_NO_CONTENT
        )


class AlbumCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsArtist]
    serializer_class = AlbumCreateSerializer
    parser_classes = [MultiPartParser, FormParser]

class MusicCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsArtist]
    serializer_class = MusicCreateSerializer
    parser_classes = [MultiPartParser, FormParser]


class MusicListView(generics.ListAPIView):
    queryset = Music.objects.all().order_by('-created_at')
    serializer_class = MusicSerializer
    permission_classes = [AllowAny] # همه می‌تونن لیست آهنگ‌ها رو ببینن

class AlbumListView(generics.ListAPIView):
    queryset = Album.objects.all().order_by('-created_at')
    serializer_class = AlbumWithMusicsSerializer
    permission_classes = [AllowAny]    

class AlbumDetailView(generics.RetrieveAPIView):
    queryset = Album.objects.all()
    serializer_class = AlbumWithMusicsSerializer
    permission_classes = [AllowAny]

class MyAlbumsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsArtist]
    serializer_class = AlbumWithMusicsSerializer
    
    def get_queryset(self):
        # برگرداندن تمام آلبوم‌های هنرمندی که لاگین کرده است
        return Album.objects.filter(artist=self.request.user.artist_profile).order_by('-created_at')