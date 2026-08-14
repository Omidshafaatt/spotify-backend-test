# music-streaming-backend/subscriptions/urls.py
from django.urls import path
from .views import ActiveSubscriptionPriceListView, CreatePaymentView, CurrentUserSubscriptionView, ZarinPalCallbackView

urlpatterns = [
    path('me/subscription/', CurrentUserSubscriptionView.as_view(), name='current-subscription'),
    path("prices/", ActiveSubscriptionPriceListView.as_view(), name="active-subscription-prices"),
    path("payments/create/", CreatePaymentView.as_view(), name="create-payment"),
    path("payments/callback/", ZarinPalCallbackView.as_view(), name="zarinpal-callback"),
]