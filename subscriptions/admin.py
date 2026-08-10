from django.contrib import admin

from .models import (
    SubscriptionPlan,
    SubscriptionPrice,
    UserSubscription,
)


class SubscriptionPriceInline(admin.TabularInline):
    model = SubscriptionPrice
    extra = 1
    fields = (
        "duration_months",
        "price",
        "is_active",
    )


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "max_daily_streams",
        "max_playlists",
        "can_download",
        "can_early_access",
        "can_view_statistics",
        "is_active",
    )

    list_filter = (
        "is_active",
        "can_download",
        "can_early_access",
        "can_view_statistics",
    )

    search_fields = ("name",)

    inlines = [SubscriptionPriceInline]


@admin.register(SubscriptionPrice)
class SubscriptionPriceAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "duration_months",
        "price",
        "is_active",
        "created_at",
    )

    list_filter = (
        "plan",
        "is_active",
        "duration_months",
    )

    search_fields = ("plan__name",)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "get_plan_name",
        "subscription_price",
        "start_date",
        "end_date",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "subscription_price__plan",
    )

    search_fields = (
        "user__email",
        "user__username",
    )

    readonly_fields = (
        "created_at",
    )

    def get_plan_name(self, obj):
        return obj.subscription_price.plan.name

    get_plan_name.short_description = "Plan"