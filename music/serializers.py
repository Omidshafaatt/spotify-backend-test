# music/serializers.py
from rest_framework import serializers
from .models import Music, Playlist, Album, MusicArtist, PlaylistMusic, MusicStream
from subscriptions.utils import get_effective_plan
from accounts.models import Artist
from accounts.models import User

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
            'likes_count', 'streams_count', 'is_liked' ,'collaborators'
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
            'genre', 'release_date', 'duration','collaborators'
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


class SearchArtistSerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(read_only=True)
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = ['id', 'stage_name', 'bio', 'is_verified', 'profile_image', 'followers_count']

    def get_profile_image(self, obj):
        if obj.user and obj.user.profile_image:
            return obj.user.profile_image.url
        return None


class SearchSongSerializer(serializers.ModelSerializer):
    artist_name = serializers.SerializerMethodField()
    artist_id = serializers.SerializerMethodField()
    streams_count = serializers.IntegerField(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Music
        fields = [
            'id', 'title', 'cover', 'audio_file', 'lyrics', 'release_date',
            'duration', 'streams_count', 'likes_count', 'is_liked',
            'artist_name', 'artist_id'
        ]

    def get_artist_name(self, obj):
        first_artist = obj.artists.first()
        return first_artist.stage_name if first_artist else "Unknown Artist"

    def get_artist_id(self, obj):
        first_artist = obj.artists.first()
        return first_artist.id if first_artist else None

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class SearchAlbumSerializer(serializers.ModelSerializer):
    artist_name = serializers.SerializerMethodField()
    artist_id = serializers.SerializerMethodField()
    song_count = serializers.SerializerMethodField()

    class Meta:
        model = Album
        fields = ['id', 'title', 'cover', 'release_date', 'artist_name', 'artist_id', 'song_count']

    def get_artist_name(self, obj):
        return obj.artist.stage_name if obj.artist else "Various Artists"

    def get_artist_id(self, obj):
        return obj.artist.id if obj.artist else None

    def get_song_count(self, obj):
        return obj.musics.count()

class SearchUserSerializer(serializers.ModelSerializer):
    followers_count = serializers.IntegerField(read_only=True)
    stage_name = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    artist_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'artist_id', 'stage_name', 'bio', 'is_verified', 'profile_image', 'followers_count', 'role']

    def get_artist_id(self, obj):
        try:
            return obj.artist_profile.id
        except Exception:
            return None

    def get_stage_name(self, obj):
        try:
            return obj.artist_profile.stage_name
        except Exception:
            return obj.display_name

    def get_bio(self, obj):
        try:
            return obj.artist_profile.bio
        except Exception:
            return ""

    def get_is_verified(self, obj):
        try:
            return obj.artist_profile.is_verified
        except Exception:
            return False

    def get_profile_image(self, obj):
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            return obj.profile_image.url
        return None