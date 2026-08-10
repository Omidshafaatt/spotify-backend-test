# music-streaming-backend/accounts/urls.py
from django.urls import path
from .views import (ArtistRequestCreateView, ArtistRequestHistoryView, ArtistRequestListView,
                    ArtistRequestUpdateView, FollowCreateView, ListenerRegisterView, LoginView,
                    ProfileView, UnfollowView, UpdateListenerProfileView, ArtistProfileView,PublicArtistDetailView)

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
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', UpdateListenerProfileView.as_view(), name='update-profile'),
    path('artist/profile/', ArtistProfileView.as_view(), name='artist-profile'),
    # ... other URLs
]