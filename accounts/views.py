# music-streaming-backend/accounts/views.py
from django.core import serializers
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import (ArtistRequestHistorySerializer, ArtistRequestListSerializer, ArtistRequestUpdateSerializer, DailyStreamsSerializer,
                           FollowSerializer, ListenerRegistrationSerializer, LoginSerializer,
                           ArtistRequestSerializer, UpdateArtistProfileSerializer, UpdateListenerProfileSerializer, UserFollowStatsSerializer, UserProfileSerializer, UnfollowSerializer,
                           ArtistProfileSerializer)
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import ArtistRequest, Follow, User
from .permissions import IsAdminOrSupport, IsListenerOrArtist
from subscriptions.models import SubscriptionPlan, UserSubscription
from django.db import models
from django.utils import timezone
from music.models import MusicStream

class ListenerRegisterView(generics.CreateAPIView):
    serializer_class = ListenerRegistrationSerializer
    permission_classes = [AllowAny]

class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'display_name': user.display_name,
                'role': user.role,
            }
        })

class ArtistRequestCreateView(generics.CreateAPIView):
    serializer_class = ArtistRequestSerializer
    permission_classes = [IsAuthenticated]
    queryset = ArtistRequest.objects.all()  # required for CreateAPIView

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # alternative to using context

class ArtistRequestListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSupport]
    serializer_class = ArtistRequestListSerializer
    queryset = ArtistRequest.objects.all().order_by('-created_at')

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

class ArtistRequestHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = ArtistRequestHistorySerializer

    def get_queryset(self):
        # Return only requests belonging to the current user, ordered by newest first
        return ArtistRequest.objects.filter(user=self.request.user).order_by('-created_at')

class ArtistRequestUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrSupport]
    serializer_class = ArtistRequestUpdateSerializer
    queryset = ArtistRequest.objects.all()
    http_method_names = ['patch', 'put']  # allow both

class FollowCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    serializer_class = FollowSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        follow_instance = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"message": f"You are now following {follow_instance.following.display_name}."},
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class UnfollowView(APIView):
    permission_classes = [IsAuthenticated, IsListenerOrArtist]
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='display_name',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Display name of the user to unfollow',
                required=True
            )
        ],
        responses={204: None, 400: None}
    )
    def delete(self, request, *args, **kwargs):
        serializer = UnfollowSerializer(data=request.query_params, context={'request': request})
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data['display_name']

        # Delete the follow relationship
        Follow.objects.filter(follower=request.user, following=target_user).delete()

        return Response(
            {"message": f"You have unfollowed {target_user.display_name}."},
            status=status.HTTP_204_NO_CONTENT
        )

class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        # Return the current authenticated user
        return self.request.user



class UpdateListenerProfileView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateListenerProfileSerializer

    def get_object(self):
        return self.request.user

    def get_effective_plan(self, user):
        """Return the active subscription plan or the Base plan if none active."""
        # Look for an active subscription (status=ACTIVE and not expired)
        active_sub = UserSubscription.objects.filter(
            user=user,
            status=UserSubscription.Status.ACTIVE
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now())
        ).first()
        if active_sub:
            return active_sub.subscription_price.plan
        # Fallback to the 'Base' plan
        try:
            return SubscriptionPlan.objects.get(name='Base')
        except SubscriptionPlan.DoesNotExist:
            # If Base plan doesn't exist, raise an error (should be created via migration)
            raise serializers.ValidationError(
                "Base subscription plan not found. Please contact support."
            )

    def update(self, request, *args, **kwargs):
        user = self.get_object()

        # Only listeners may update their profile via this endpoint
        if user.role != User.Role.LISTENER:
            return Response(
                {"detail": "Only listeners can update their profile."},
                status=status.HTTP_403_FORBIDDEN
            )

        # If a profile image is being uploaded, check subscription permissions
        if 'profile_image' in request.FILES:
            plan = self.get_effective_plan(user)
            if not plan.can_upload_profile_image:
                return Response(
                    {"detail": "Your subscription plan does not allow uploading profile images."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Perform the update
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class ArtistProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ArtistProfileSerializer

    def get_object(self):
        user = self.request.user
        # Ensure user is an artist and has an artist_profile
        if user.role != User.Role.ARTIST:
            # Return 403 or 404 – we'll raise a 404 for security (don't leak info)
            self.kwargs['pk'] = None  # trigger 404
        # The serializer expects a User instance, so return it
        return user

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        if user is None or not hasattr(user, 'artist_profile'):
            return Response(
                {"detail": "Artist profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(user)
        return Response(serializer.data)


from .models import Artist
from .serializers import PublicArtistSerializer

class PublicArtistDetailView(generics.RetrieveAPIView):
    queryset = Artist.objects.all()
    serializer_class = PublicArtistSerializer
    permission_classes = [AllowAny]

class CurrentUserFollowStatsView(generics.GenericAPIView):
    """
    GET /api/users/me/follow-stats/
    Returns the follower and following counts for the currently authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserFollowStatsSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        # Count followers (users who follow this user)
        followers_count = Follow.objects.filter(following=user).count()
        # Count followings (users this user follows)
        following_count = Follow.objects.filter(follower=user).count()

        data = {
            'followers_count': followers_count,
            'following_count': following_count,
        }
        serializer = self.get_serializer(data)
        return Response(serializer.data)
    

class UserFollowStatsByDisplayNameView(generics.GenericAPIView):
    """
    GET /api/users/follow-stats/?display_name=<name>
    Returns the follower and following counts for a user with the given display_name.
    """
    permission_classes = [IsAuthenticated]  # or allow any
    serializer_class = UserFollowStatsSerializer

    def get(self, request, *args, **kwargs):
        display_name = request.query_params.get('display_name')
        if not display_name:
            return Response(
                {'error': 'display_name query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Since display_name is not unique, we need to decide behavior.
            # Option 1: return the first match (not recommended).
            # Option 2: require a unique field. But display_name is not unique.
            # Better: return error if multiple users have the same display_name.
            users = User.objects.filter(display_name__iexact=display_name)
            if not users.exists():
                raise NotFound('No user found with this display name.')
            if users.count() > 1:
                return Response(
                    {'error': f'Multiple users found with display name "{display_name}". Please use a more specific identifier.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user = users.first()
        except User.DoesNotExist:
            raise NotFound('User not found.')

        followers_count = Follow.objects.filter(following=user).count()
        following_count = Follow.objects.filter(follower=user).count()

        data = {
            'followers_count': followers_count,
            'following_count': following_count,
        }
        serializer = self.get_serializer(data)
        return Response(serializer.data)


class CurrentUserDailyStreamsView(generics.GenericAPIView):
    """
    GET /api/music/me/daily-streams/
    Returns average daily streams for the currently authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DailyStreamsSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        data = self._compute_stats(user)
        serializer = self.get_serializer(data)
        return Response(serializer.data)

    def _compute_stats(self, user):
        total_streams = MusicStream.objects.filter(user=user).count()
        if total_streams == 0:
            return {
                'total_streams': 0,
                'days_active': 0,
                'average_daily_streams': 0.0,
            }

        # Get earliest stream
        earliest = MusicStream.objects.filter(user=user).earliest('started_at')
        first_date = earliest.started_at.date()
        today = timezone.now().date()
        days_active = (today - first_date).days + 1  # inclusive count

        avg = total_streams / days_active if days_active > 0 else 0.0
        return {
            'total_streams': total_streams,
            'days_active': days_active,
            'average_daily_streams': round(avg, 2),
        }


class UserDailyStreamsByDisplayNameView(generics.GenericAPIView):
    """
    GET /api/music/users/daily-streams/?display_name=<name>
    Returns average daily streams for a user with the given display_name.
    """
    permission_classes = [IsAuthenticated]  # or AllowAny if public
    serializer_class = DailyStreamsSerializer

    def get(self, request, *args, **kwargs):
        display_name = request.query_params.get('display_name')
        if not display_name:
            return Response(
                {'error': 'display_name query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        users = User.objects.filter(display_name__iexact=display_name)
        if not users.exists():
            raise NotFound('No user found with this display name.')
        if users.count() > 1:
            return Response(
                {'error': f'Multiple users found with display name "{display_name}". Please use a more specific identifier.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = users.first()

        # Use the same helper as above
        data = self._compute_stats(user)
        serializer = self.get_serializer(data)
        return Response(serializer.data)

    def _compute_stats(self, user):
        total_streams = MusicStream.objects.filter(user=user).count()
        if total_streams == 0:
            return {
                'total_streams': 0,
                'days_active': 0,
                'average_daily_streams': 0.0,
            }

        earliest = MusicStream.objects.filter(user=user).earliest('started_at')
        first_date = earliest.started_at.date()
        today = timezone.now().date()
        days_active = (today - first_date).days + 1

        avg = total_streams / days_active if days_active > 0 else 0.0
        return {
            'total_streams': total_streams,
            'days_active': days_active,
            'average_daily_streams': round(avg, 2),
        }


class UpdateArtistProfileView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateArtistProfileSerializer

    def get_object(self):
        return self.request.user

    def get_effective_plan(self, user):
        """Return the active subscription plan or the Base plan if none active."""
        active_sub = UserSubscription.objects.filter(
            user=user,
            status=UserSubscription.Status.ACTIVE
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now())
        ).first()
        if active_sub:
            return active_sub.subscription_price.plan
        # Fallback to the 'Base' plan
        try:
            return SubscriptionPlan.objects.get(name='Base')
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError(
                "Base subscription plan not found. Please contact support."
            )

    def update(self, request, *args, **kwargs):
        user = self.get_object()

        # Only artists may update their profile via this endpoint
        if user.role != User.Role.ARTIST:
            return Response(
                {"detail": "Only artists can update their profile."},
                status=status.HTTP_403_FORBIDDEN
            )

        # If a profile image is being uploaded, check subscription permissions
        if 'profile_image' in request.FILES or 'profile_image' in request.data:
            plan = self.get_effective_plan(user)
            if not plan.can_upload_profile_image:
                return Response(
                    {"detail": "Your subscription plan does not allow uploading profile images."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Perform the update (serializer handles both User and Artist fields)
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)