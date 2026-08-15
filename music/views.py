# music/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Max, Q, Count

from .models import Playlist, PlaylistMusic, Album, Music, MusicStream
from .serializers import (ArtistStatisticsSerializer, PlaylistSerializer, PlaylistCreateSerializer, 
                          AddRemoveMusicSerializer, AlbumCreateSerializer, 
                          MusicCreateSerializer, MusicSerializer, 
                          AlbumWithMusicsSerializer,PlaylistDetailSerializer,
                          SearchSongSerializer, SearchAlbumSerializer, SearchArtistSerializer)
from .permissions import IsListenerOrArtist, IsArtist

from rest_framework.exceptions import PermissionDenied, NotFound

from accounts.models import Artist
from subscriptions.utils import get_effective_plan

class PlaylistCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = PlaylistCreateSerializer
    parser_classes = [MultiPartParser, FormParser]
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class PlaylistUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = PlaylistSerializer
    http_method_names = ['patch', 'put']
    parser_classes = [MultiPartParser, FormParser]
    def get_queryset(self):
        return Playlist.objects.filter(owner=self.request.user)

class PlaylistDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = PlaylistSerializer 
    def get_queryset(self):
        return Playlist.objects.filter(owner=self.request.user)

class AddMusicToPlaylistView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = AddRemoveMusicSerializer

    def get_playlist(self, pk):
        try:
            return Playlist.objects.get(pk=pk, owner=self.request.user)
        except Playlist.DoesNotExist:
            return None

    def post(self, request, pk, *args, **kwargs):
        playlist = self.get_playlist(pk)
        if playlist is None:
            return Response({"detail": "Playlist not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        music = serializer.validated_data['music_id']

        if PlaylistMusic.objects.filter(playlist=playlist, music=music).exists():
            return Response({"detail": "Already in playlist."}, status=status.HTTP_400_BAD_REQUEST)

        max_pos = PlaylistMusic.objects.filter(playlist=playlist).aggregate(Max('position'))['position__max']
        position = (max_pos or 0) + 1

        PlaylistMusic.objects.create(playlist=playlist, music=music, position=position)
        return Response({"detail": "Music added."}, status=status.HTTP_201_CREATED)

class RemoveMusicFromPlaylistView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = AddRemoveMusicSerializer

    def get_playlist(self, pk):
        try:
            return Playlist.objects.get(pk=pk, owner=self.request.user)
        except Playlist.DoesNotExist:
            return None

    def delete(self, request, pk, *args, **kwargs):
        playlist = self.get_playlist(pk)
        if playlist is None:
            return Response({"detail": "Playlist not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        music = serializer.validated_data['music_id']

        try:
            playlist_music = PlaylistMusic.objects.get(playlist=playlist, music=music)
            playlist_music.delete()
            return Response({"detail": "Music removed."}, status=status.HTTP_204_NO_CONTENT)
        except PlaylistMusic.DoesNotExist:
            return Response({"detail": "Music not in playlist."}, status=status.HTTP_404_NOT_FOUND)

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
    permission_classes = [AllowAny]

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
        return Album.objects.filter(artist=self.request.user.artist_profile).order_by('-created_at')

class ToggleLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        music = get_object_or_404(Music, pk=pk)
        if request.user in music.likes.all():
            music.likes.remove(request.user)
            return Response({"detail": "Unliked", "is_liked": False}, status=status.HTTP_200_OK)
        else:
            music.likes.add(request.user)
            return Response({"detail": "Liked", "is_liked": True}, status=status.HTTP_200_OK)

class RecordStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        music = get_object_or_404(Music, pk=pk)
        MusicStream.objects.create(user=request.user, music=music)
        return Response({"detail": "Stream recorded successfully"}, status=status.HTTP_201_CREATED)

class MyPlaylistsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PlaylistSerializer

    def get_queryset(self):
        # برگرداندن تمام پلی‌لیست‌های کاربری که لاگین کرده
        return Playlist.objects.filter(owner=self.request.user).order_by('-created_at')

class PlaylistDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PlaylistDetailSerializer
    
    def get_queryset(self):
        # کاربر فقط بتونه پلی‌لیست‌های خودش رو ببینه
        return Playlist.objects.filter(owner=self.request.user)

class ArtistStatisticsView(APIView):
    """
    GET /api/artists/<int:artist_id>/statistics/
    Returns total streams and unique listeners for a given artist.
    Only accessible if the logged-in user's subscription plan allows viewing statistics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, artist_id):
        # 1. Check subscription permission
        plan = get_effective_plan(request.user)
        if plan is None or not plan.can_view_statistics:
            raise PermissionDenied(
                "Your subscription plan does not allow viewing artist statistics."
            )

        # 2. Retrieve the artist
        try:
            artist = Artist.objects.get(id=artist_id)
        except Artist.DoesNotExist:
            raise NotFound("Artist not found.")

        # 3. Compute streams
        # All MusicStream records for musics that have this artist as a collaborator
        streams_qs = MusicStream.objects.filter(
            music__music_artists__artist_id=artist_id
        )

        total_streams = streams_qs.count()
        unique_listeners = streams_qs.values('user').distinct().count()

        # 4. Serialize and respond
        data = {
            'total_streams': total_streams,
            'unique_listeners': unique_listeners,
        }
        serializer = ArtistStatisticsSerializer(data)
        return Response(serializer.data)



class UnifiedSearchView(APIView):
    """
    GET /api/search/
    Query params:
      - q (string) – search query
      - sort (listeners|date) – default 'listeners'
      - limit (int) – default 10
    """
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        sort = request.query_params.get('sort', 'listeners')
        limit = int(request.query_params.get('limit', 10))

        if not query:
            return Response({'songs': [], 'albums': [], 'artists': []})

        # ---- Songs ----
        songs_qs = Music.objects.filter(Q(title__icontains=query))
        songs_qs = songs_qs.annotate(streams_count=Count('streams'))
        if sort == 'listeners':
            songs_qs = songs_qs.order_by('-streams_count')
        else:  # date
            songs_qs = songs_qs.order_by('-release_date')
        songs = songs_qs[:limit]
        song_serializer = SearchSongSerializer(songs, many=True, context={'request': request})

        # ---- Albums ----
        albums_qs = Album.objects.filter(Q(title__icontains=query))
        if sort == 'listeners':
            albums_qs = albums_qs.annotate(
                total_streams=Count('musics__streams')
            ).order_by('-total_streams')
        else:
            albums_qs = albums_qs.order_by('-release_date')
        albums = albums_qs[:limit]
        album_serializer = SearchAlbumSerializer(albums, many=True)

        # ---- Artists ----
        artists_qs = Artist.objects.filter(
            Q(stage_name__icontains=query) |
            Q(user__display_name__icontains=query)
        )
        artists_qs = artists_qs.annotate(
            followers_count=Count('user__followers')
        )
        if sort == 'listeners':
            artists_qs = artists_qs.order_by('-followers_count')
        else:
            artists_qs = artists_qs.order_by('-created_at')
        artists = artists_qs[:limit]
        artist_serializer = SearchArtistSerializer(artists, many=True)

        return Response({
            'songs': song_serializer.data,
            'albums': album_serializer.data,
            'artists': artist_serializer.data,
        })