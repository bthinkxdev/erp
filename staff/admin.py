from django.contrib import admin

from .models import Staff
from utils.queryset import secure_queryset


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "vendor",
        "whatsapp_number",
        "is_active",
        "can_view_all_collections",
        "can_edit_collection",
        "can_view_reports",
        "can_export_data",
        "can_manage_products",
        "can_manage_categories",
        "can_add_customers",
        "can_edit_customers",
        "created_at",
    )
    list_filter = ("is_active", "vendor")
    search_fields = ("user__username", "user__email", "whatsapp_number")
    autocomplete_fields = ("user", "vendor")
    ordering = ("-created_at",)
    list_select_related = ("user", "vendor")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return secure_queryset(qs, request)

