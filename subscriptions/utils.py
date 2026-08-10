# music-streaming-backend/subscriptions/utils.py
from django.db import models
from django.utils import timezone
from .models import SubscriptionPlan, UserSubscription


def get_effective_plan(user):
    """
    Return the active subscription plan for the user,
    or the default 'Base' plan if no active subscription exists.
    """
    active_sub = UserSubscription.objects.filter(
        user=user,
        status=UserSubscription.Status.ACTIVE
    ).filter(
        models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now())
    ).first()
    if active_sub:
        return active_sub.subscription_price.plan
    try:
        return SubscriptionPlan.objects.get(name='Base')
    except SubscriptionPlan.DoesNotExist:
        return None