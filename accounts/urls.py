from django.urls import path
from .views import (ArtistRequestCreateView, ArtistRequestHistoryView, ArtistRequestListView,
                    ArtistRequestUpdateView, CurrentUserDailyStreamsView, CurrentUserFollowStatsView, FollowCreateView, ListenerRegisterView, LoginView,
                    ProfileView, UnfollowView, UpdateArtistProfileView, UpdateListenerProfileView, ArtistProfileView,PublicArtistDetailView, UserDailyStreamsByDisplayNameView, UserFollowStatsByDisplayNameView)

urlpatterns = [
    path('artists/<int:pk>/', PublicArtistDetailView.as_view(), name='public-artist-detail'),
    path('register/listener/', ListenerRegisterView.as_view(), name='listener-register'),
    path('login/', LoginView.as_view(), name='login'),
    path('artist-request/', ArtistRequestCreateView.as_view(), name='artist-request'),
    path('artist-requests/', ArtistRequestListView.as_view(), name='artist-requests-list'),
    path('artist-requests/history/', ArtistRequestHistoryView.as_view(), name='artist-request-history'),
    path('artist-requests/<int:pk>/', ArtistRequestUpdateView.as_view(), name='artist-request-update'),
    path('follow/', FollowCreateView.as_view(), name='follow'),
    path('unfollow/', UnfollowView.as_view(), name='unfollow'),
    path('profile/me/', ProfileView.as_view(), name='profile'),
    path('profile/update/', UpdateListenerProfileView.as_view(), name='update-profile'),
    path('artist/profile/me/', ArtistProfileView.as_view(), name='artist-profile'),
    path('users/me/follow-stats/', CurrentUserFollowStatsView.as_view(), name='current-user-follow-stats'),
    path('users/follow-stats/', UserFollowStatsByDisplayNameView.as_view(), name='user-follow-stats-by-display-name'),
    path('me/daily-streams/', CurrentUserDailyStreamsView.as_view(), name='current-user-daily-streams'),
    path('users/daily-streams/', UserDailyStreamsByDisplayNameView.as_view(), name='user-daily-streams-by-display-name'),
    # ... other URLs
]