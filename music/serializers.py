# music-streaming-backend/music/serializers.py
from rest_framework import serializers
from .models import Music, Playlist, Album
from subscriptions.utils import get_effective_plan

class PlaylistSerializer(serializers.ModelSerializer):
    """Base serializer for listing and updating playlists."""
    class Meta:
        model = Playlist
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlaylistCreateSerializer(PlaylistSerializer):
    """Adds validation for max_playlists on creation."""
    def validate(self, data):
        request = self.context.get('request')
        if request:
            user = request.user
            plan = get_effective_plan(user)
            if plan is None:
                raise serializers.ValidationError("No subscription plan found. Please contact support.")
            if plan.max_playlists is not None:
                current_count = Playlist.objects.filter(owner=user).count()
                if current_count >= plan.max_playlists:
                    raise serializers.ValidationError(
                        f"You have reached the maximum number of playlists ({plan.max_playlists}) allowed by your plan."
                    )
        return data

class AddRemoveMusicSerializer(serializers.Serializer):
    music_id = serializers.IntegerField()

    def validate_music_id(self, value):
        try:
            music = Music.objects.get(pk=value)
        except Music.DoesNotExist:
            raise serializers.ValidationError("Music not found.")
        return music



class MusicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Music
        fields = [
            'id', 'title', 'audio_file', 'lyrics', 'cover',
            'genre', 'release_date', 'duration', 'created_at'
        ]


class AlbumWithMusicsSerializer(serializers.ModelSerializer):
    musics = MusicSerializer(many=True, read_only=True)

    class Meta:
        model = Album
        fields = ['id', 'title', 'cover', 'release_date', 'created_at', 'musics']


