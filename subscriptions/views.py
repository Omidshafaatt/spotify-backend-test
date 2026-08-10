# music-streaming-backend/subscriptions/views.py
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import models
from .models import UserSubscription
from .serializers import SubscriptionPlanSerializer, CurrentUserSubscriptionSerializer
from rest_framework import generics, status
from .utils import get_effective_plan

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