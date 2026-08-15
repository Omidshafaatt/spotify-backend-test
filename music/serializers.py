# music/serializers.py
from rest_framework import serializers
from .models import Music, Playlist, Album, MusicArtist, PlaylistMusic, MusicStream
from subscriptions.utils import get_effective_plan
from accounts.models import Artist

class ArtistBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['id', 'stage_name']

class PlaylistSerializer(serializers.ModelSerializer):
    """Base serializer for listing and updating playlists."""
    # فیلد جدید برای شمردن تعداد آهنگ‌های داخل پلی‌لیست
    songs_count = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ['id', 'name', 'cover', 'songs_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'songs_count']

    def get_songs_count(self, obj):
        return obj.musics.count()

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
    artists = ArtistBasicSerializer(many=True, read_only=True)
    
    # فیلدهای محاسباتی جدید برای لایک و استریم
    likes_count = serializers.SerializerMethodField()
    streams_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Music
        fields = [
            'id', 'title', 'album', 'audio_file', 'lyrics', 'cover',
            'genre', 'release_date', 'duration', 'created_at', 'artists',
            'likes_count', 'streams_count', 'is_liked' 
        ]

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_streams_count(self, obj):
        return obj.streams.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

class AlbumWithMusicsSerializer(serializers.ModelSerializer):
    musics = MusicSerializer(many=True, read_only=True)

    class Meta:
        model = Album
        fields = ['id', 'title', 'cover', 'release_date', 'created_at', 'musics']

class AlbumCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ['id', 'title', 'cover', 'release_date']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['artist'] = user.artist_profile
        return super().create(validated_data)

class MusicCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Music
        fields = [
            'id', 'title', 'album', 'audio_file', 'lyrics', 'cover',
            'genre', 'release_date', 'duration'
        ]

    def create(self, validated_data):
        music = Music.objects.create(**validated_data)
        user = self.context['request'].user
        artist_profile = user.artist_profile
        MusicArtist.objects.create(music=music, artist=artist_profile)
        return music

class PlaylistDetailSerializer(serializers.ModelSerializer):
    musics = MusicSerializer(many=True, read_only=True)

    class Meta:
        model = Playlist
        # فیلد cover اینجا جا مانده بود که اضافه شد!
        fields = ['id', 'name', 'cover', 'created_at', 'updated_at', 'musics']

class ArtistStatisticsSerializer(serializers.Serializer):
    total_streams = serializers.IntegerField()
    unique_listeners = serializers.IntegerField()