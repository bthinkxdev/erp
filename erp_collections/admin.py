from django.contrib import admin

from .models import Collection
from utils.queryset import secure_queryset


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vendor",
        "staff",
        "customer",
        "amount",
        "remark",
        "day_number",
        "week_number",
        "date",
    )
    list_filter = ("vendor", "staff", "week_number", "date")
    search_fields = ("customer__name", "staff__user__username")
    autocomplete_fields = ("vendor", "staff", "customer")
    ordering = ("-date",)
    list_select_related = ("vendor", "staff", "customer")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return secure_queryset(qs, request)

