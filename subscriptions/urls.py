# music-streaming-backend/subscriptions/urls.py
from django.urls import path
from .views import CurrentUserSubscriptionView

urlpatterns = [
    path('me/subscription/', CurrentUserSubscriptionView.as_view(), name='current-subscription'),
]