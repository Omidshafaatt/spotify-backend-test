# music-streaming-backend/subscriptions/urls.py
from django.urls import path
from .views import ActiveSubscriptionPriceListView, CreatePaymentView, CurrentUserSubscriptionView, ZarinPalCallbackView

urlpatterns = [
    # endpoint to get the current user's subscription details
    path('me/subscription/', CurrentUserSubscriptionView.as_view(), name='current-subscription'),

    # endpoint to get the list of active subscription prices
    path("prices/", ActiveSubscriptionPriceListView.as_view(), name="active-subscription-prices"),

    # endpoint to create a payment for a subscription
    path("payments/create/", CreatePaymentView.as_view(), name="create-payment"),
    path("payments/callback/", ZarinPalCallbackView.as_view(), name="zarinpal-callback"),
]