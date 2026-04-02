from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class UserAdminConfig(UserAdmin):
    model = User
    search_fields = ("username", "email")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    ordering = ("-created_at",)

    list_display = (
        "id",
        "username",
        "email",
        "role",
        "is_staff",
        "is_superuser",
        "is_active",
        "created_at",
        "updated_at",
    )

    readonly_fields = ("created_at", "updated_at")

    fieldsets = UserAdmin.fieldsets + (
        (
            "Role & access",
            {
                "fields": (
                    "role",
                )
            },
        ),
    )

