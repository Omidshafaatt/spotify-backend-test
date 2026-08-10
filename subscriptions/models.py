# music-streaming-backend/subscriptions/models.py
from django.conf import settings
from django.db import models


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50, unique=True)

    max_daily_streams = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of daily streams. NULL means unlimited."
    )

    max_playlists = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of playlists. NULL means unlimited."
    )

    can_upload_profile_image = models.BooleanField(default=False)
    can_download = models.BooleanField(default=False)
    can_early_access = models.BooleanField(default=False)
    can_view_statistics = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SubscriptionPrice(models.Model):
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="prices",
    )

    duration_months = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "duration_months"],
                condition=models.Q(is_active=True),
                name="unique_active_price_per_plan_duration",
            )
        ]

    def __str__(self):
        return f"{self.plan.name} - {self.duration_months} months"


class UserSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    subscription_price = models.ForeignKey(
        SubscriptionPrice,
        on_delete=models.PROTECT,
        related_name="user_subscriptions",
    )

    start_date = models.DateTimeField()
    end_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.subscription_price.plan.name}"