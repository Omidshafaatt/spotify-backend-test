# music-streaming-backend/subscriptions/serializers.py
from rest_framework import serializers
from .models import SubscriptionPlan, SubscriptionPrice, SubscriptionPrice

class SubscriptionPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPrice
        fields = ['id', 'duration_months', 'price', 'is_active']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    prices = SubscriptionPriceSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'max_daily_streams', 'max_playlists',
            'can_upload_profile_image', 'can_download', 'can_early_access',
            'can_view_statistics', 'is_active', 'prices'
        ]

class ActiveSubscriptionPriceSerializer(serializers.ModelSerializer):
    """Serializer for active prices – includes nested plan info."""
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = SubscriptionPrice
        fields = [
            "id",
            "plan",
            "duration_months",
            "price",
            "is_active",
        ]

class CurrentUserSubscriptionSerializer(serializers.Serializer):
    plan = SubscriptionPlanSerializer()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    duration_months = serializers.IntegerField(allow_null=True)
    start_date = serializers.DateTimeField(allow_null=True)
    end_date = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    is_default_base = serializers.BooleanField()


class PaymentCreateSerializer(serializers.Serializer):
    price_id = serializers.IntegerField()

    def validate_price_id(self, value):
        try:
            price = SubscriptionPrice.objects.select_related("plan").get(
                id=value,
                is_active=True,
                plan__is_active=True,
            )
        except SubscriptionPrice.DoesNotExist:
            raise serializers.ValidationError(
                "Selected subscription price does not exist or is inactive."
            )

        self._price = price
        return value

    @property
    def price(self):
        return getattr(self, "_price", None)


class DashboardStatsSerializer(serializers.Serializer):
    current_month_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    active_users = serializers.IntegerField()
    subscription_distribution = serializers.DictField(
        child=serializers.IntegerField()
    )

class SubscriptionPriceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPrice
        fields = ['id', 'duration_months', 'price', 'is_active']  # add duration_months read-only
        read_only_fields = ['id', 'duration_months']


class SubscriptionPlanDetailSerializer(serializers.ModelSerializer):
    prices = SubscriptionPriceUpdateSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'prices']