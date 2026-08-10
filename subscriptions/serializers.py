# music-streaming-backend/subscriptions/serializers.py
from rest_framework import serializers
from .models import SubscriptionPlan, SubscriptionPrice

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

class CurrentUserSubscriptionSerializer(serializers.Serializer):
    plan = SubscriptionPlanSerializer()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    duration_months = serializers.IntegerField(allow_null=True)
    start_date = serializers.DateTimeField(allow_null=True)
    end_date = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    is_default_base = serializers.BooleanField()