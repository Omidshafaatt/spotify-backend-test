# music/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Max

from .models import Playlist, PlaylistMusic, Album, Music, MusicStream
from .serializers import (PlaylistSerializer, PlaylistCreateSerializer, 
                          AddRemoveMusicSerializer, AlbumCreateSerializer, 
                          MusicCreateSerializer, MusicSerializer, 
                          AlbumWithMusicsSerializer)
from .permissions import IsListenerOrArtist, IsArtist

class PlaylistCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = PlaylistCreateSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class PlaylistUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = PlaylistSerializer
    http_method_names = ['patch', 'put']

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