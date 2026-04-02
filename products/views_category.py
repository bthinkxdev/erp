from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from utils.queryset import secure_queryset
from utils.security import (
    get_secure_object,
    staff_category_mutation_allowed,
    vendor_may_soft_delete,
)
from utils.vendor import get_vendor_from_request
from .forms import ProductCategoryForm
from .models import ProductCategory


def _vendor(request):
    return getattr(request, "vendor", None) or get_vendor_from_request(request)


def _category_queryset(request):
    return secure_queryset(ProductCategory.objects.all(), request).order_by("name")


@login_required
@require_GET
def category_modal(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not staff_category_mutation_allowed(request):
        return HttpResponseForbidden()

    return render(
        request,
        "products/partials/category_modal_page.html",
        {
            "categories": _category_queryset(request),
            "dismiss_url": reverse("products:category_dismiss"),
        },
    )


@login_required
@require_GET
def category_dismiss(request):
    return HttpResponse("")


@login_required
@require_GET
def category_panel(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not staff_category_mutation_allowed(request):
        return HttpResponseForbidden()

    return render(
        request,
        "products/partials/category_list.html",
        {"categories": _category_queryset(request)},
    )


@login_required
@require_http_methods(["GET", "POST"])
def category_add(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not staff_category_mutation_allowed(request):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = ProductCategoryForm(request.POST, request.FILES, vendor=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, "Category saved.")
            return render(
                request,
                "products/partials/category_list.html",
                {"categories": _category_queryset(request)},
            )
    else:
        form = ProductCategoryForm(vendor=vendor)

    return render(
        request,
        "products/partials/category_form.html",
        {
            "form": form,
            "submit_url": reverse("products:category_add"),
            "cancel_url": reverse("products:category_panel"),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def category_edit(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not staff_category_mutation_allowed(request):
        return HttpResponseForbidden()

    category = get_secure_object(ProductCategory.objects.all(), request, pk=pk)

    if request.method == "POST":
        form = ProductCategoryForm(
            request.POST, request.FILES, instance=category, vendor=vendor
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return render(
                request,
                "products/partials/category_list.html",
                {"categories": _category_queryset(request)},
            )
    else:
        form = ProductCategoryForm(instance=category, vendor=vendor)

    return render(
        request,
        "products/partials/category_form.html",
        {
            "form": form,
            "submit_url": reverse("products:category_edit", kwargs={"pk": pk}),
            "cancel_url": reverse("products:category_panel"),
        },
    )


@login_required
@require_POST
def category_delete(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not vendor_may_soft_delete(request):
        return HttpResponseForbidden()

    category = get_secure_object(ProductCategory.objects.all(), request, pk=pk)
    category.delete()
    messages.success(request, "Category archived (removed from lists).")

    return render(
        request,
        "products/partials/category_list.html",
        {"categories": _category_queryset(request)},
    )
