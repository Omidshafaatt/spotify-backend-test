# rooms/serializers.py
from rest_framework import serializers
from .models import Room


class RoomCreateSerializer(serializers.ModelSerializer):
    invite_link = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'invite_link']

    def get_invite_link(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/room/{obj.id}/')
        return f'/room/{obj.id}/'

# rooms/serializers.py
from rest_framework import serializers
from accounts.models import User
from .models import Room


class RoomMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'display_name', 'profile_image']


class RoomStatusSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(source='member_count', read_only=True)
    current_song_url = serializers.SerializerMethodField()
    members = RoomMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = [
            'id',
            'members',
            'members_count',
            'current_song',
            'current_song_url',
            'current_song_title',
            'current_position',
            'is_playing',
            'created_at',
            'updated_at',
        ]

    def get_current_song_url(self, obj):
        if obj.current_song:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.current_song.url)
            return obj.current_song.url
        return None

class UploadSongSerializer(serializers.Serializer):
    audio_file = serializers.FileField()
    title = serializers.CharField(required=False, allow_blank=True)

    def validate_audio_file(self, value):
        # Optional: validate file extension
        allowed_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Unsupported file type. Please upload MP3, WAV, or OGG.")
        # Optional: limit file size (e.g., 20MB)
        if value.size > 20 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds 20MB limit.")
        return value

