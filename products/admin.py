from django.contrib import admin

from .models import Product, ProductCategory
from utils.queryset import secure_queryset


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "is_active", "image")
    search_fields = ("name",)
    list_filter = ("vendor", "is_active")
    list_select_related = ("vendor",)
    ordering = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return secure_queryset(qs, request)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "vendor", "price", "mrp", "is_active", "created_at")
    list_filter = ("vendor", "is_active", "category")
    search_fields = ("name", "description")
    autocomplete_fields = ("vendor", "category")
    list_select_related = ("vendor", "category")
    ordering = ("-created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return secure_queryset(qs, request)

