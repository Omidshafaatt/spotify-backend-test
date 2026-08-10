from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Artist


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Use email as the main identifier
    ordering = ("email",)
    list_display = (
        "email",
        "username",
        "display_name",
        "role",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "username", "display_name")

    # Fieldsets for the change form
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {
            "fields": (
                "username",
                "display_name",
                "birth_date",
                "gender",
                "profile_image",
            )
        }),
        (_("Role & permissions"), {
            "fields": (
                "role",
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    # Fieldsets for the add form
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "username",
                "display_name",
                "password1",
                "password2",
                "role",
                "is_staff",
                "is_superuser",
            ),
        }),
    )

    # Required because USERNAME_FIELD = "email"
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = (
        "stage_name",
        "user",
        "is_verified",
        "verified_at",
        "created_at",
    )
    list_filter = ("is_verified",)
    search_fields = ("stage_name", "user__email", "user__username", "user__display_name")
    raw_id_fields = ("user",)          # nicer when you have many users
    readonly_fields = ("created_at", "updated_at", "verified_at")