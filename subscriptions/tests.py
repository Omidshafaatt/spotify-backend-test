# subscriptions/tests.py
from datetime import date
from decimal import Decimal
from unittest.mock import patch, Mock

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from .models import (
    SubscriptionPlan,
    SubscriptionPrice,
    UserSubscription,
    PaymentTransaction,
)


class SubscriptionAPITests(APITestCase):

    # --------------------------------------------------
    # Helper methods
    # --------------------------------------------------

    def create_user(
        self,
        email="user@example.com",
        display_name="TestUser",
        role=None,
    ):
        if role is None:
            role = User.Role.LISTENER

        return User.objects.create_user(
            username=f"test_{display_name}",
            email=email,
            display_name=display_name,
            password="TestPassword123!",
            birth_date=date(2000, 1, 1),
            gender="male",
            role=role,
        )

    def create_plan(
        self,
        name="Silver",
        is_active=True,
    ):
        return SubscriptionPlan.objects.create(
            name=name,
            max_daily_streams=100,
            max_playlists=10,
            can_upload_profile_image=True,
            can_download=True,
            can_early_access=False,
            can_view_statistics=True,
            is_active=is_active,
        )

    def create_price(
        self,
        plan,
        duration_months=1,
        price=Decimal("100000.00"),
        is_active=True,
    ):
        return SubscriptionPrice.objects.create(
            plan=plan,
            duration_months=duration_months,
            price=price,
            is_active=is_active,
        )

    # --------------------------------------------------
    # 1. Only active prices of active plans are returned
    # --------------------------------------------------

    def test_active_subscription_prices_only(self):
        active_plan = self.create_plan(
            name="Silver",
            is_active=True,
        )

        inactive_plan = self.create_plan(
            name="Gold",
            is_active=False,
        )

        active_price = self.create_price(
            plan=active_plan,
            duration_months=1,
            price=Decimal("100000.00"),
            is_active=True,
        )

        # This price is inactive
        self.create_price(
            plan=active_plan,
            duration_months=3,
            price=Decimal("250000.00"),
            is_active=False,
        )

        # This price is active, but its plan is inactive
        self.create_price(
            plan=inactive_plan,
            duration_months=1,
            price=Decimal("200000.00"),
            is_active=True,
        )

        url = reverse("active-subscription-prices")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.data), 1)

        self.assertEqual(
            response.data[0]["id"],
            active_price.id,
        )

        self.assertEqual(
            response.data[0]["duration_months"],
            1,
        )

        self.assertEqual(
            Decimal(str(response.data[0]["price"])),
            Decimal("100000.00"),
        )

    # --------------------------------------------------
    # 2. Creating a payment successfully
    # --------------------------------------------------

    @patch("subscriptions.views.requests.post")
    def test_create_payment_success(self, mock_post):
        user = self.create_user()

        plan = self.create_plan(
            name="Silver",
            is_active=True,
        )

        price = self.create_price(
            plan=plan,
            duration_months=3,
            price=Decimal("300000.00"),
            is_active=True,
        )

        # Mock ZarinPal response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": {
                "authority": "TEST_AUTHORITY_123",
                "code": 100,
            }
        }

        mock_post.return_value = mock_response

        self.client.force_authenticate(user=user)

        url = reverse("create-payment")

        response = self.client.post(
            url,
            {
                "price_id": price.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        # Check response
        self.assertEqual(
            response.data["authority"],
            "TEST_AUTHORITY_123",
        )

        self.assertIn("payment_id", response.data)
        self.assertIn("payment_url", response.data)

        # Check database
        payment = PaymentTransaction.objects.get(
            id=response.data["payment_id"]
        )

        self.assertEqual(payment.user, user)
        self.assertEqual(payment.subscription_price, price)

        self.assertEqual(
            payment.amount,
            Decimal("300000.00"),
        )

        self.assertEqual(
            payment.status,
            PaymentTransaction.Status.PENDING,
        )

        self.assertEqual(
            payment.authority,
            "TEST_AUTHORITY_123",
        )

        # Make sure ZarinPal was actually called once
        mock_post.assert_called_once()

    # --------------------------------------------------
    # 3. User with an active subscription cannot
    #    create another payment
    # --------------------------------------------------

    @patch("subscriptions.views.requests.post")
    def test_create_payment_with_active_subscription_fails(
        self,
        mock_post,
    ):
        user = self.create_user()

        plan = self.create_plan(
            name="Silver",
            is_active=True,
        )

        price = self.create_price(
            plan=plan,
            duration_months=1,
            price=Decimal("100000.00"),
            is_active=True,
        )

        UserSubscription.objects.create(
            user=user,
            subscription_price=price,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),
            status=UserSubscription.Status.ACTIVE,
        )

        self.client.force_authenticate(user=user)

        url = reverse("create-payment")

        response = self.client.post(
            url,
            {
                "price_id": price.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.data["detail"],
            "You already have an active subscription.",
        )

        # No new payment should have been created
        self.assertEqual(
            PaymentTransaction.objects.filter(user=user).count(),
            0,
        )

        # ZarinPal should not be called
        mock_post.assert_not_called()

    # --------------------------------------------------
    # 4. Cancelled payment callback
    # --------------------------------------------------

    def test_payment_callback_cancelled(self):
        user = self.create_user()

        plan = self.create_plan(
            name="Silver",
            is_active=True,
        )

        price = self.create_price(
            plan=plan,
            duration_months=1,
            price=Decimal("100000.00"),
            is_active=True,
        )

        payment = PaymentTransaction.objects.create(
            user=user,
            subscription_price=price,
            amount=price.price,
            authority="CANCEL_AUTHORITY",
            status=PaymentTransaction.Status.PENDING,
        )

        url = reverse("zarinpal-callback")

        response = self.client.get(
            url,
            {
                "Authority": "CANCEL_AUTHORITY",
                "Status": "NOK",
            },
        )

        self.assertEqual(response.status_code, 302)

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            PaymentTransaction.Status.CANCELLED,
        )

        # No subscription should be created
        self.assertFalse(
            UserSubscription.objects.filter(
                user=user
            ).exists()
        )

    # --------------------------------------------------
    # 5. Successful payment callback creates subscription
    # --------------------------------------------------

    @patch("subscriptions.views.requests.post")
    def test_payment_callback_success(
        self,
        mock_post,
    ):
        user = self.create_user()

        plan = self.create_plan(
            name="Gold",
            is_active=True,
        )

        price = self.create_price(
            plan=plan,
            duration_months=3,
            price=Decimal("500000.00"),
            is_active=True,
        )

        payment = PaymentTransaction.objects.create(
            user=user,
            subscription_price=price,
            amount=price.price,
            authority="SUCCESS_AUTHORITY",
            status=PaymentTransaction.Status.PENDING,
        )

        # Mock ZarinPal verification response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "code": 100,
                "ref_id": "REF123456",
            }
        }

        mock_post.return_value = mock_response

        url = reverse("zarinpal-callback")

        response = self.client.get(
            url,
            {
                "Authority": "SUCCESS_AUTHORITY",
                "Status": "OK",
            },
        )

        self.assertEqual(response.status_code, 302)

        # -----------------------------
        # Check payment
        # -----------------------------

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            PaymentTransaction.Status.SUCCESS,
        )

        self.assertEqual(
            payment.ref_id,
            "REF123456",
        )

        self.assertIsNotNone(payment.paid_at)
        self.assertIsNotNone(payment.verified_at)

        # -----------------------------
        # Check subscription
        # -----------------------------

        subscription = UserSubscription.objects.get(
            user=user
        )

        self.assertEqual(
            subscription.subscription_price,
            price,
        )

        self.assertEqual(
            subscription.status,
            UserSubscription.Status.ACTIVE,
        )

        self.assertIsNotNone(subscription.start_date)
        self.assertIsNotNone(subscription.end_date)

        # Three-month subscription should have
        # an end date after the start date.
        self.assertGreater(
            subscription.end_date,
            subscription.start_date,
        )

        # ZarinPal verification should be called once
        mock_post.assert_called_once()