from django.urls import path
from .views import ArtistRequestCreateView, ArtistRequestHistoryView, ArtistRequestListView, ArtistRequestUpdateView, ListenerRegisterView, LoginView

urlpatterns = [
    path('register/listener/', ListenerRegisterView.as_view(), name='listener-register'),
    path('login/', LoginView.as_view(), name='login'),
    path('artist-request/', ArtistRequestCreateView.as_view(), name='artist-request'),
    path('artist-requests/', ArtistRequestListView.as_view(), name='artist-requests-list'),
    path('artist-requests/history/', ArtistRequestHistoryView.as_view(), name='artist-request-history'),
    path('artist-requests/<int:pk>/', ArtistRequestUpdateView.as_view(), name='artist-request-update'),
    # ... other URLs
]