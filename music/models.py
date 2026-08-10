# music-streaming-backend/music/models.py
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Artist


class Album(models.Model):
    
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name="albums",
        null=True,
        blank=True
    )
    
    title = models.CharField(max_length=200)
    cover = models.ImageField(upload_to="albums/covers/%Y/%m/", null=True, blank=True)
    release_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Music(models.Model):
    title = models.CharField(max_length=200)

    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="musics",
    )

    audio_file = models.FileField(
        upload_to="tracks/audio/%Y/%m/",
    )

    lyrics = models.TextField(
        blank=True,
    )

    cover = models.ImageField(
        upload_to="tracks/covers/%Y/%m/",
        null=True,
        blank=True,
    )

    genre = models.CharField(
        max_length=100,
        blank=True,
    )

    release_date = models.DateField()

    duration = models.DurationField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    artists = models.ManyToManyField(
        Artist,
        through="MusicArtist",
        related_name="musics",
    )

    def __str__(self):
        return self.title


class MusicArtist(models.Model):
    music = models.ForeignKey(
        Music,
        on_delete=models.CASCADE,
        related_name="music_artists",
    )

    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        related_name="music_artists",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["music", "artist"],
                name="unique_music_artist",
            ),
        ]

    def __str__(self):
        return f"{self.music.title} - {self.artist.stage_name}"


class Playlist(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="playlists",
    )

    name = models.CharField(
        max_length=200,
    )

    musics = models.ManyToManyField(
        Music,
        through="PlaylistMusic",
        related_name="playlists",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.owner.username} - {self.name}"


class PlaylistMusic(models.Model):
    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name="playlist_musics",
    )

    music = models.ForeignKey(
        Music,
        on_delete=models.CASCADE,
        related_name="playlist_musics",
    )

    position = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    added_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["playlist", "music"],
                name="unique_music_in_playlist",
            ),
            models.UniqueConstraint(
                fields=["playlist", "position"],
                name="unique_playlist_position",
            ),
        ]

        ordering = ["position"]

    def __str__(self):
        return f"{self.playlist.name} - {self.music.title}"

class MusicStream(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="music_streams",
    )

    music = models.ForeignKey(
        Music,
        on_delete=models.CASCADE,
        related_name="streams",
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    listened_duration = models.DurationField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.user.email} - {self.music.title}"
