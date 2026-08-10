import secrets
import string
from datetime import date
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import ArtistRequest, User, Artist
from django.contrib.auth import authenticate


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