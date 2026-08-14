# music-streaming-backend/accounts/urls.py
from django.urls import path
from .views import (ArtistRequestCreateView, ArtistRequestHistoryView, ArtistRequestListView,
                    ArtistRequestUpdateView, CurrentUserDailyStreamsView, CurrentUserFollowStatsView, FollowCreateView, ListenerRegisterView, LoginView,
                    ProfileView, UnfollowView, UpdateArtistProfileView, UpdateListenerProfileView, ArtistProfileView,PublicArtistDetailView, UserDailyStreamsByDisplayNameView, UserFollowStatsByDisplayNameView)

urlpatterns = [
    # register and login endpoints
    path('register/listener/', ListenerRegisterView.as_view(), name='listener-register'),
    path('login/', LoginView.as_view(), name='login'),

    # request for becoming an artist endpoint
    path('artist-request/', ArtistRequestCreateView.as_view(), name='artist-request'),
    # list all artist requests endpoint (for admin users)
    path('artist-requests/', ArtistRequestListView.as_view(), name='artist-requests-list'),
    # list all artist requests made by the current user
    path('artist-requests/history/', ArtistRequestHistoryView.as_view(), name='artist-request-history'),
    # update (approve or reject) an artist request endpoint (for admin users)
    path('artist-requests/<int:pk>/', ArtistRequestUpdateView.as_view(), name='artist-request-update'),
    
    # follow and unfollow endpoints
    path('follow/', FollowCreateView.as_view(), name='follow'),
    path('unfollow/', UnfollowView.as_view(), name='unfollow'),

    # data that shows in profile page both listener and artist (login required)
    path('profile/me/', ProfileView.as_view(), name='profile'),
    path('users/me/follow-stats/', CurrentUserFollowStatsView.as_view(), name='current-user-follow-stats'),
    path('me/daily-streams/', CurrentUserDailyStreamsView.as_view(), name='current-user-daily-streams'),

    # additional data that shows in profile page for artist (login required)
    path('artist/profile/me/', ArtistProfileView.as_view(), name='artist-profile'),

    # update profile endpoints for both listener and artist (login required)
    path('profile/update/', UpdateListenerProfileView.as_view(), name='update-profile'),
    path('profile/artist/update/', UpdateArtistProfileView.as_view(), name='update-artist-profile'),
    
    path('users/follow-stats/', UserFollowStatsByDisplayNameView.as_view(), name='user-follow-stats-by-display-name'),
    path('users/daily-streams/', UserDailyStreamsByDisplayNameView.as_view(), name='user-daily-streams-by-display-name'),

    path('artists/<int:pk>/', PublicArtistDetailView.as_view(), name='public-artist-detail'),
    # ... other URLs
]