from __future__ import annotations

from django.shortcuts import get_object_or_404, render

from utils.store import resolve_store_context, store_staff_query_fragment

from .models import Product, ProductCategory


def store_home(request, vendor_id):
    vendor, staff = resolve_store_context(request, vendor_id)
    categories = (
        ProductCategory.objects.filter(vendor_id=vendor.pk, is_active=True)
        .order_by("name")
    )
    return render(
        request,
        "store/home.html",
        {
            "store_vendor": vendor,
            "store_staff": staff,
            "store_staff_query": store_staff_query_fragment(staff),
            "categories": categories,
        },
    )


def store_product_detail(request, vendor_id, product_id):
    vendor, staff = resolve_store_context(request, vendor_id)
    product = get_object_or_404(Product, pk=product_id, vendor_id=vendor.pk, is_active=True)
    images = [img for img in [product.image or None, product.image2 or None, product.image3 or None] if img]
    return render(
        request,
        "store/product_detail.html",
        {
            "store_vendor": vendor,
            "store_staff": staff,
            "store_staff_query": store_staff_query_fragment(staff),
            "product": product,
            "images": images,
        },
    )


def store_category_products(request, vendor_id, category_id):
    vendor, staff = resolve_store_context(request, vendor_id)
    category = get_object_or_404(
        ProductCategory,
        pk=category_id,
        vendor_id=vendor.pk,
        is_active=True,
    )
    products = (
        Product.objects.filter(
            vendor_id=vendor.pk,
            category_id=category.pk,
            is_active=True,
        )
        .select_related("category", "vendor")
        .order_by("name")
    )
    return render(
        request,
        "store/product_list.html",
        {
            "store_vendor": vendor,
            "store_staff": staff,
            "store_staff_query": store_staff_query_fragment(staff),
            "category": category,
            "products": products,
        },
    )
