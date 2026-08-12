# music-streaming-backend/accounts/serializers.py
import secrets
import string
from datetime import date
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import ArtistRequest, Follow, User, Artist
from django.contrib.auth import authenticate
from music.models import Album, Music, MusicStream
from music.serializers import AlbumWithMusicsSerializer, MusicSerializer
from drf_spectacular.utils import extend_schema_field


class ListenerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'email', 'display_name', 'birth_date', 'gender',
            'password', 'password2'
        )
        extra_kwargs = {
            'email': {'required': True},
            'display_name': {'required': True},
            'birth_date': {'required': True},
            'gender': {'required': True},
        }

    def validate(self, attrs):
        # Check password match
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        # Validate birth_date (not in the future)
        birth_date = attrs.get('birth_date')
        if birth_date and birth_date > date.today():
            raise serializers.ValidationError({"birth_date": "Birth date cannot be in the future."})

        # Validate gender (only 'male' or 'female')
        gender = attrs.get('gender')
        if gender and gender.lower() not in ('male', 'female'):
            raise serializers.ValidationError({"gender": "Gender must be either 'male' or 'female'."})

        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_display_name(self, value):
        # Case‑insensitive uniqueness check
        if User.objects.filter(display_name__iexact=value).exists():
            raise serializers.ValidationError("This display name is already taken.")
        return value

    def create(self, validated_data):
        # Remove password2; we don't store it
        validated_data.pop('password2')

        # Generate a random unique username
        username = self._generate_unique_username()
        validated_data['username'] = username

        # Set role to LISTENER
        validated_data['role'] = User.Role.LISTENER

        # Create user with hashed password
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

        return user

    def _generate_unique_username(self, length=10):
        alphabet = string.ascii_lowercase + string.digits
        while True:
            username = ''.join(secrets.choice(alphabet) for _ in range(length))
            if not User.objects.filter(username=username).exists():
                return username

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'")

        data['user'] = user
        return data

class ArtistRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtistRequest
        fields = ['id', 'stage_name', 'portfolio', 'status', 'reason', 'created_at']
        read_only_fields = ['id', 'status', 'reason', 'created_at']

    def validate(self, data):
        user = self.context['request'].user

        # Check if user is a listener
        if user.role != User.Role.LISTENER:
            raise serializers.ValidationError("Only listeners can request to become an artist.")

        # Check if user already has an artist profile
        if hasattr(user, 'artist_profile') and user.artist_profile is not None:
            raise serializers.ValidationError("You are already an artist.")

        # Check if user already has a pending request
        if ArtistRequest.objects.filter(user=user, status=ArtistRequest.Status.PENDING).exists():
            raise serializers.ValidationError("You already have a pending artist request.")

        return data

    def create(self, validated_data):
        # Set user from request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

from .models import ArtistRequest


class ArtistRequestListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email')
    user_display_name = serializers.CharField(source='user.display_name')

    class Meta:
        model = ArtistRequest
        fields = [
            'id', 'user_email', 'user_display_name',
            'stage_name', 'portfolio', 'status', 'reason', 'created_at'
        ]

class ArtistRequestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtistRequest
        fields = ['id', 'stage_name', 'portfolio', 'status', 'reason', 'created_at']


class ArtistRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtistRequest
        fields = ['status', 'reason']
        extra_kwargs = {
            'reason': {'required': False, 'allow_blank': True},
        }

    def validate(self, data):
        instance = self.instance
        if not instance or instance.status != ArtistRequest.Status.PENDING:
            raise serializers.ValidationError("This request has already been processed.")

        new_status = data.get('status')
        if new_status not in (ArtistRequest.Status.APPROVED, ArtistRequest.Status.REJECTED):
            raise serializers.ValidationError("Status must be 'approved' or 'rejected'.")

        # If approving, ensure user doesn't already have an artist profile
        if new_status == ArtistRequest.Status.APPROVED:
            if Artist.objects.filter(user=instance.user).exists():
                raise serializers.ValidationError("This user is already an artist.")

        return data

    def update(self, instance, validated_data):
        # Update status and reason
        instance.status = validated_data.get('status', instance.status)
        instance.reason = validated_data.get('reason', instance.reason)
        instance.save()

        # If approved, create Artist and update user role
        if instance.status == ArtistRequest.Status.APPROVED:
            user = instance.user
            # Create Artist record
            Artist.objects.create(
                user=user,
                stage_name=instance.stage_name,
                bio="",  # default empty bio
                is_verified=False
            )
            # Update user role to ARTIST
            user.role = User.Role.ARTIST
            user.save(update_fields=['role'])

        return instance


class FollowSerializer(serializers.Serializer):
    display_name = serializers.CharField()

    def validate_display_name(self, value):
        try:
            target_user = User.objects.get(display_name__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this display name does not exist.")
        return target_user

    def validate(self, data):
        follower = self.context['request'].user
        following = data['display_name']

        # Follower must be listener or artist
        if follower.role not in (User.Role.LISTENER, User.Role.ARTIST):
            raise serializers.ValidationError("You must be a listener or artist to follow someone.")

        # Target must be listener or artist
        if following.role not in (User.Role.LISTENER, User.Role.ARTIST):
            raise serializers.ValidationError("You can only follow listeners or artists.")

        # Cannot follow yourself
        if follower == following:
            raise serializers.ValidationError("You cannot follow yourself.")

        # Check if already following (prevents duplicate follow)
        if Follow.objects.filter(follower=follower, following=following).exists():
            raise serializers.ValidationError("You are already following this user.")

        return data

    def create(self, validated_data):
        follower = self.context['request'].user
        following = validated_data['display_name']
        return Follow.objects.create(follower=follower, following=following)

class UnfollowSerializer(serializers.Serializer):
    display_name = serializers.CharField()

    def validate_display_name(self, value):
        try:
            target_user = User.objects.get(display_name__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this display name does not exist.")
        return target_user

    def validate(self, data):
        follower = self.context['request'].user
        following = data['display_name']

        # Cannot unfollow yourself (though a follow record shouldn't exist, just in case)
        if follower == following:
            raise serializers.ValidationError("You cannot unfollow yourself.")

        # Check if a follow relationship exists
        if not Follow.objects.filter(follower=follower, following=following).exists():
            raise serializers.ValidationError("You are not following this user.")

        return data

class UserProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'display_name',
            'birth_date', 'gender', 'role', 'profile_image',
            'created_at', 'updated_at'
        ]

    def get_profile_image(self, obj) -> str:   # add -> str
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            return obj.profile_image.url
        # Return default image URL
        default_image_url = f"profile_images/base_profile.jpg"
        # If you have a specific default image file, you can append extension, e.g., .png
        # For simplicity, we assume the default image is named 'base_profile' (without extension)
        # or you can use a full URL.
        return default_image_url

class UpdateListenerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['display_name', 'profile_image']
        extra_kwargs = {
            'display_name': {'required': False},
            'profile_image': {'required': False},
        }

    def validate_display_name(self, value):
        # Ensure uniqueness, excluding the current user
        if User.objects.filter(display_name__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("This display name is already taken.")
        return value

class ArtistProfileSerializer(serializers.Serializer):
    # We'll use SerializerMethodField for computed fields
    albums = serializers.SerializerMethodField()
    singles = serializers.SerializerMethodField()
    total_streams = serializers.SerializerMethodField()
    # Basic artist info
    stage_name = serializers.CharField(source='artist_profile.stage_name')
    bio = serializers.CharField(source='artist_profile.bio')
    is_verified = serializers.BooleanField(source='artist_profile.is_verified')

    class Meta:
        # The source is a User instance, but we access artist_profile
        fields = ['stage_name', 'bio', 'is_verified', 'albums', 'singles', 'total_streams']

    @extend_schema_field(AlbumWithMusicsSerializer(many=True))
    def get_albums(self, obj):
        # obj is a User instance
        artist = obj.artist_profile
        # Get all distinct albums that contain at least one music by this artist
        albums = Album.objects.filter(musics__artists=artist).distinct().order_by('-release_date')
        return AlbumWithMusicsSerializer(albums, many=True).data
    
    @extend_schema_field(MusicSerializer(many=True))
    def get_singles(self, obj):
        artist = obj.artist_profile
        # Get music that belongs to this artist, has no album, and order by release date
        singles = Music.objects.filter(artists=artist, album__isnull=True).order_by('-release_date')
        return MusicSerializer(singles, many=True).data

    @extend_schema_field(serializers.IntegerField())
    def get_total_streams(self, obj):
        artist = obj.artist_profile
        # Count all streams for all music of this artist
        return MusicStream.objects.filter(music__artists=artist).count()

class PublicArtistSerializer(serializers.ModelSerializer):
    singles = serializers.SerializerMethodField()
    albums = serializers.SerializerMethodField()
    user_display_name = serializers.SerializerMethodField() # تبدیل به متد امن

    class Meta:
        model = Artist
        fields = ['id', 'user_display_name', 'stage_name', 'bio', 'is_verified', 'singles', 'albums']

    def get_user_display_name(self, obj):
        # گرفتن نام کاربری به صورت کاملاً امن که تحت هیچ شرایطی ارور ندهد
        try:
            if hasattr(obj, 'user') and obj.user:
                return getattr(obj.user, 'display_name', obj.user.username)
            return "Unknown"
        except Exception:
            return "Unknown"

    def get_singles(self, obj):
        singles = Music.objects.filter(artists=obj, album__isnull=True).order_by('-release_date')
        # پاس دادن کانتکست برای کار کردن صحیح لایک‌ها
        return MusicSerializer(singles, many=True, context=self.context).data

    def get_albums(self, obj):
        albums = Album.objects.filter(musics__artists=obj).distinct().order_by('-release_date')
        return AlbumWithMusicsSerializer(albums, many=True, context=self.context).data