from django.contrib import admin

from .models import Customer
from utils.queryset import secure_queryset


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_code", "name", "phone", "loan_amount", "assigned_day", "staff", "vendor", "created_at")
    list_filter = ("vendor", "staff")
    search_fields = ("name", "phone", "customer_code")
    autocomplete_fields = ("vendor", "staff")
    ordering = ("-created_at",)
    list_select_related = ("vendor", "staff", "staff__user")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return secure_queryset(qs, request)

