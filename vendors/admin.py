from django.contrib import admin

from utils.queryset import secure_queryset

from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "whatsapp_number",
        "owner",
        "is_active",
        "staff_see_all_customers",
        "created_at",
    )
    list_filter = ("is_active", "staff_see_all_customers")
    search_fields = ("name", "whatsapp_number", "owner__username", "owner__email")
    autocomplete_fields = ("owner",)
    ordering = ("-created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return secure_queryset(qs, request)

