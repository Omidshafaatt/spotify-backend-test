# music-streaming-backend/subscriptions/views.py
import requests
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from django.db import models, transaction
from .models import PaymentTransaction, SubscriptionPrice, UserSubscription
from .serializers import PaymentCreateSerializer, SubscriptionPlanDetailSerializer, SubscriptionPlanSerializer, CurrentUserSubscriptionSerializer, ActiveSubscriptionPriceSerializer, SubscriptionPriceUpdateSerializer
from rest_framework import generics, status
from .utils import get_effective_plan
from rest_framework.views import APIView, settings
from rest_framework.generics import GenericAPIView
from django.shortcuts import redirect

class CurrentUserSubscriptionView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurrentUserSubscriptionSerializer   # ← required

    def get(self, request, *args, **kwargs):
        user = request.user
        plan = get_effective_plan(user)
        if plan is None:
            return Response(
                {"detail": "No subscription plan found."},
                status=status.HTTP_404_NOT_FOUND
            )

        active_sub = UserSubscription.objects.filter(
            user=user,
            status=UserSubscription.Status.ACTIVE
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now())
        ).first()

        if active_sub:
            data = {
                'plan': SubscriptionPlanSerializer(plan).data,
                'price': active_sub.subscription_price.price,
                'duration_months': active_sub.subscription_price.duration_months,
                'start_date': active_sub.start_date,
                'end_date': active_sub.end_date,
                'status': active_sub.status,
                'is_default_base': False,
            }
        else:
            data = {
                'plan': SubscriptionPlanSerializer(plan).data,
                'price': None,
                'duration_months': None,
                'start_date': None,
                'end_date': None,
                'status': 'base',
                'is_default_base': True,
            }
        return Response(data)


class ActiveSubscriptionPriceListView(generics.ListAPIView):
    """
    Returns all active SubscriptionPrice records
    (only prices whose plan is also active).
    """
    serializer_class = ActiveSubscriptionPriceSerializer
    permission_classes = [AllowAny]          # change to IsAuthenticated if you want

    def get_queryset(self):
        return (
            SubscriptionPrice.objects
            .filter(
                is_active=True,
                plan__is_active=True,          # only prices belonging to active plans
            )
            .select_related("plan")            # performance
            .order_by("plan__name", "duration_months")
        )


class CreatePaymentView(GenericAPIView):
    serializer_class = PaymentCreateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        price = serializer.price
        user = request.user
        now = timezone.now()

        # Lock the user row so two simultaneous payment requests
        # cannot both pass the "no active subscription" check.
        with transaction.atomic():
            locked_user = (
                type(user)
                .objects
                .select_for_update()
                .get(pk=user.pk)
            )

            active_subscription = (
                UserSubscription.objects
                .select_for_update()
                .filter(
                    user=locked_user,
                    status=UserSubscription.Status.ACTIVE,
                )
                .first()
            )

            if active_subscription:
                # If the subscription is actually expired but its status
                # has not been updated yet, mark it as expired.
                if (
                    active_subscription.end_date is not None
                    and active_subscription.end_date <= now
                ):
                    active_subscription.status = (
                        UserSubscription.Status.EXPIRED
                    )
                    active_subscription.save(update_fields=["status"])
                else:
                    return Response(
                        {
                            "detail": (
                                "You already have an active subscription."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Store the amount at the time of transaction creation.
            amount = price.price

            payment = PaymentTransaction.objects.create(
                user=locked_user,
                subscription_price=price,
                amount=amount,
                status=PaymentTransaction.Status.PENDING,
            )

        # ---------------------------------------------------------
        # Send payment request to ZarinPal
        # ---------------------------------------------------------

        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": str(int(amount)),  # Convert Decimal to string
            "description": (
                f"Subscription purchase - "
                f"{price.plan.name} - "
                f"{price.duration_months} months"
            ),
            "description": "test",
            "callback_url": settings.ZARINPAL_CALLBACK_URL,
        }

        try:
            response = requests.post(
                settings.ZARINPAL_REQUEST_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            response.raise_for_status()
            response_data = response.json()

        # except requests.RequestException:
        #     payment.status = PaymentTransaction.Status.FAILED
        #     payment.save(update_fields=["status"])

        #     return Response(
        #         {
        #             "detail": (
        #                 "Could not connect to the payment gateway."
        #             )
        #         },
        #         status=status.HTTP_502_BAD_GATEWAY,
        #     )
        except requests.RequestException as exc:
            payment.status = PaymentTransaction.Status.FAILED
            payment.save(update_fields=["status"])

            return Response(
                {
                    "detail": "Could not connect to the payment gateway.",
                    "error": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ---------------------------------------------------------
        # Process ZarinPal response
        # ---------------------------------------------------------

        data = response_data.get("data") or {}

        authority = data.get("authority")
        code = data.get("code")

        if not authority:
            payment.status = PaymentTransaction.Status.FAILED
            payment.save(update_fields=["status"])

            return Response(
                {
                    "detail": "Payment gateway rejected the payment request.",
                    "gateway_response": response_data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.authority = authority
        payment.save(update_fields=["authority"])

        payment_url = (
            f"{settings.ZARINPAL_START_PAY_URL}/{authority}"
        )

        return Response(
            {
                "payment_id": payment.id,
                "authority": authority,
                "payment_url": payment_url,
            },
            status=status.HTTP_201_CREATED,
        )

class ZarinPalCallbackView(APIView):
    """
    Handles the redirect from ZarinPal after the user completes
    or cancels the payment.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        authority = request.query_params.get("Authority")
        payment_status = request.query_params.get("Status")

        # ---------------------------------------------------------
        # 1. Validate callback parameters
        # ---------------------------------------------------------

        if not authority:
            return redirect(
                f"{settings.FRONTEND_PAYMENT_RESULT_URL}?status=failed"
                f"&reason=missing_authority"
            )

        try:
            payment = (
                PaymentTransaction.objects
                .select_related(
                    "user",
                    "subscription_price",
                    "subscription_price__plan",
                )
                .get(authority=authority)
            )
        except PaymentTransaction.DoesNotExist:
            return redirect(
                f"{settings.FRONTEND_PAYMENT_RESULT_URL}?status=failed"
                f"&reason=transaction_not_found"
            )

        # ---------------------------------------------------------
        # 2. Idempotency
        # ---------------------------------------------------------
        # If this callback is received again after a successful
        # payment, don't create another subscription.

        if payment.status == PaymentTransaction.Status.SUCCESS:
            return redirect(
                f"{settings.FRONTEND_PAYMENT_RESULT_URL}"
                f"?status=success&payment_id={payment.id}"
            )

        # ---------------------------------------------------------
        # 3. User cancelled or payment failed
        # ---------------------------------------------------------

        if payment_status != "OK":
            payment.status = PaymentTransaction.Status.CANCELLED
            payment.save(update_fields=["status"])

            return redirect(
                f"{settings.FRONTEND_PAYMENT_RESULT_URL}"
                f"?status=cancelled&payment_id={payment.id}"
            )

        # ---------------------------------------------------------
        # 4. Verify payment with ZarinPal
        # ---------------------------------------------------------

        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": str(int(payment.amount)),
            "authority": payment.authority,
        }

        try:
            response = requests.post(
                settings.ZARINPAL_VERIFY_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                },
                timeout=15,
            )

            response_data = response.json()

        except (requests.RequestException, ValueError):
            payment.status = PaymentTransaction.Status.FAILED
            payment.save(update_fields=["status"])

            return redirect(
                f"{settings.FRONTEND_PAYMENT_RESULT_URL}"
                f"?status=failed&reason=verification_error"
            )

        # ---------------------------------------------------------
        # 5. Read ZarinPal verification result
        # ---------------------------------------------------------

        data = response_data.get("data") or {}
        code = data.get("code")

        # ZarinPal:
        # 100 = successful verification
        # 101 = already verified
        if code is not None and code not in (100, 101): # looks like the code in the response is None even when the payment is successful, so we check for None first

            payment.status = PaymentTransaction.Status.FAILED
            payment.save(update_fields=["status"])

            return redirect(
                f"{settings.FRONTEND_PAYMENT_RESULT_URL}"
                f"?status=failed&payment_id={payment.id}"
            )

        # ---------------------------------------------------------
        # 6. Mark payment successful + create subscription
        # ---------------------------------------------------------

        with transaction.atomic():
            locked_payment = (
                PaymentTransaction.objects
                .select_for_update()
                .select_related(
                    "user",
                    "subscription_price",
                    "subscription_price__plan",
                )
                .get(pk=payment.pk)
            )

            # Another callback/request may have completed it while
            # this request was being processed.
            if locked_payment.status != PaymentTransaction.Status.SUCCESS:

                now = timezone.now()

                # Re-check active subscription before creating a new one.
                # This protects against race conditions.
                active_subscription = (
                    UserSubscription.objects
                    .select_for_update()
                    .filter(
                        user=locked_payment.user,
                        status=UserSubscription.Status.ACTIVE,
                    )
                    .first()
                )

                if active_subscription:
                    if (
                        active_subscription.end_date is not None
                        and active_subscription.end_date <= now
                    ):
                        active_subscription.status = (
                            UserSubscription.Status.EXPIRED
                        )
                        active_subscription.save(
                            update_fields=["status"]
                        )
                    else:
                        # A successful payment exists, but the user
                        # already has an active subscription.
                        #
                        # We do NOT create another subscription.
                        locked_payment.status = (
                            PaymentTransaction.Status.FAILED
                        )
                        locked_payment.save(update_fields=["status"])

                        return redirect(
                            f"{settings.FRONTEND_PAYMENT_RESULT_URL}"
                            f"?status=failed"
                            f"&reason=active_subscription"
                            f"&payment_id={locked_payment.id}"
                        )

                # ---------------------------------------------
                # Create the subscription
                # ---------------------------------------------

                start_date = now

                duration_months = (
                    locked_payment.subscription_price.duration_months
                )

                # We use months rather than a fixed number of days.
                # This handles durations such as 1, 3, 6 and 12 months.
                from dateutil.relativedelta import relativedelta

                end_date = start_date + relativedelta(
                    months=duration_months
                )

                UserSubscription.objects.create(
                    user=locked_payment.user,
                    subscription_price=(
                        locked_payment.subscription_price
                    ),
                    start_date=start_date,
                    end_date=end_date,
                    status=UserSubscription.Status.ACTIVE,
                )

                # ---------------------------------------------
                # Update payment
                # ---------------------------------------------

                locked_payment.status = PaymentTransaction.Status.SUCCESS

                if data.get("ref_id") is not None:
                    locked_payment.ref_id = str(data["ref_id"])

                locked_payment.paid_at = now
                locked_payment.verified_at = now

                locked_payment.save(
                    update_fields=[
                        "status",
                        "ref_id",
                        "paid_at",
                        "verified_at",
                    ]
                )

        # ---------------------------------------------------------
        # 7. Redirect user back to frontend
        # ---------------------------------------------------------

        return redirect(
            f"{settings.FRONTEND_PAYMENT_RESULT_URL}"
            f"?status=success"
            f"&payment_id={payment.id}"
        )


# subscriptions/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Sum
from django.utils import timezone
from django.db import models
from accounts.models import User
from .models import PaymentTransaction, UserSubscription, SubscriptionPlan
from .serializers import DashboardStatsSerializer
from accounts.permissions import IsAdmin  # or define your own


class AdminDashboardStatsView(APIView):
    """
    GET /api/admin/dashboard/stats/
    Returns:
      - current_month_revenue: total amount from successful payments in the current month
      - active_users: number of users with an active subscription (status=ACTIVE and not expired)
      - subscription_distribution: counts per plan (Base, Silver, Gold) for all users
    """
    permission_classes = [IsAuthenticated, IsAdmin]  # only admin/support

    def get(self, request):
        now = timezone.now()
        # ---- Current month revenue ----
        # Sum of amount from successful transactions in the current month (by paid_at)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        revenue = PaymentTransaction.objects.filter(
            status=PaymentTransaction.Status.SUCCESS,
            paid_at__gte=current_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        # ---- Active users ----
        # Users with at least one active subscription (status=ACTIVE and end_date >= today or null)
        active_users = UserSubscription.objects.filter(
            status=UserSubscription.Status.ACTIVE
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        ).values('user').distinct().count()

        # ---- Subscription distribution ----
        total_users = User.objects.count()

        # Get users with active paid plans (Silver, Gold)
        # We need to get the latest active subscription per user, then group by plan name
        # For simplicity, we'll count users with any active subscription to each plan.
        # But if a user has multiple, we count them once per plan (could skew).
        # Better: count distinct users per plan based on their current active subscription.
        # We'll use a subquery or annotate.
        # Approach: get all active subscriptions, then for each user, pick the one with latest start_date? We'll just count distinct users per plan.
        # But a user could have both Silver and Gold? Not likely, but we'll use distinct.
        plan_counts = {}
        plans = SubscriptionPlan.objects.all()
        for plan in plans:
            # Count distinct users with at least one active subscription to this plan
            count = UserSubscription.objects.filter(
                subscription_price__plan=plan,
                status=UserSubscription.Status.ACTIVE
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
            ).values('user').distinct().count()
            plan_counts[plan.name.lower()] = count

        # Base = total_users - sum of paid plan counts (assuming Base is the default for those without any subscription)
        paid_count = sum(plan_counts.values())
        base_count = total_users - paid_count
        distribution = {
            'base': base_count,
            **{name.lower(): count for name, count in plan_counts.items()}
        }

        # Ensure all plans are present; if some plan is missing, set to 0
        # The frontend expects keys: base, silver, gold – but we can send all plan names dynamically.
        # The frontend in renderSystemTab expects static keys. We'll keep that expectation and only return those.
        # But we can also send all plans; frontend can adapt.

        data = {
            'current_month_revenue': revenue,
            'active_users': active_users,
            'subscription_distribution': {
                'base': distribution.get('base', 0),
                'silver': distribution.get('silver', 0),
                'gold': distribution.get('gold', 0),
            }
        }
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)


class AdminPlansListView(APIView):
    """
    GET /api/admin/plans/
    Returns all active subscription plans with their prices.
    Admin only.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        serializer = SubscriptionPlanDetailSerializer(plans, many=True)
        return Response(serializer.data)


class AdminUpdatePriceView(APIView):
    """
    PATCH /api/admin/subscription-prices/<int:price_id>/
    Update price of a specific SubscriptionPrice.
    Admin only.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, price_id):
        try:
            price_obj = SubscriptionPrice.objects.get(id=price_id)
        except SubscriptionPrice.DoesNotExist:
            return Response({'detail': 'Price not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubscriptionPriceUpdateSerializer(price_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)