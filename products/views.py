from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from utils.queryset import secure_queryset
from utils.security import (
    get_secure_object,
    staff_product_mutation_allowed,
    vendor_may_soft_delete,
)
from utils.vendor import get_vendor_from_request
from .forms import ProductForm
from .models import Product, ProductCategory


def _vendor(request):
    return getattr(request, "vendor", None) or get_vendor_from_request(request)


def _store_share_absolute_url(request):
    """
    Absolute public store URL for the current tenant.

    - Staff users: `/store/<vendor_id>/?staff=<Staff.pk>` so WhatsApp orders use their number.
    - Vendor accounts: `/store/<vendor_id>/` — orders use the business WhatsApp unless the URL
      includes `?staff=`. Use Staff → Edit → “Copy member’s store link” for a team member.
    """
    vendor = _vendor(request)
    if not vendor:
        return ""
    path = reverse("store:home", kwargs={"vendor_id": vendor.pk})
    url = request.build_absolute_uri(path)
    user = request.user
    if getattr(user, "role", None) == "staff":
        sp = getattr(user, "staff_profile", None)
        if sp is not None:
            url = f"{url}?staff={sp.pk}"
    return url


def _htmx_targets_list_fragment(request) -> bool:
    """Only in-list search/filter use the small partial; other HTMX (e.g. form hx-target=body) must get full page."""
    if not request.headers.get("HX-Request"):
        return False
    tid = (request.headers.get("HX-Target") or "").strip().lstrip("#")
    return tid == "products-list-fragment"


def _redirect_products_list(request):
    url = reverse("products:list")
    if request.headers.get("HX-Request"):
        response = HttpResponseRedirect(url)
        response["HX-Redirect"] = url
        return response
    return redirect("products:list")


@login_required
def product_list(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()

    qs = secure_queryset(Product.objects.all(), request).select_related("category")

    if request.GET.get("active") == "1":
        qs = qs.filter(is_active=True)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(name__icontains=q)

    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)

    total_count = qs.count()
    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    category_choices = secure_queryset(ProductCategory.objects.all(), request).order_by("name")

    ctx = {
        "products": page_obj.object_list,
        "page_obj": page_obj,
        "total_count": total_count,
        "category_choices": category_choices,
        "products_add_url": reverse("products:add"),
        "store_share_url": _store_share_absolute_url(request),
    }

    if _htmx_targets_list_fragment(request):
        return render(request, "products/partials/products_list_inner.html", ctx)

    return render(request, "products/list.html", ctx)


@login_required
@require_http_methods(["GET", "POST"])
def product_add(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not staff_product_mutation_allowed(request):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, vendor=vendor)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = vendor
            product.save()
            messages.success(request, f"Product '{product.name}' added.")
            return _redirect_products_list(request)
    else:
        form = ProductForm(initial={"is_active": True}, vendor=vendor)

    return render(
        request,
        "products/form.html",
        {"form": form, "store_share_url": _store_share_absolute_url(request)},
    )


@login_required
@require_http_methods(["GET", "POST"])
def product_edit(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not staff_product_mutation_allowed(request):
        return HttpResponseForbidden()

    product = get_secure_object(Product.objects.all(), request, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product, vendor=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated.")
            return _redirect_products_list(request)
    else:
        form = ProductForm(instance=product, vendor=vendor)

    return render(
        request,
        "products/form.html",
        {"form": form, "store_share_url": _store_share_absolute_url(request)},
    )


@login_required
@require_http_methods(["POST", "DELETE"])
def product_delete(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not vendor_may_soft_delete(request):
        return HttpResponseForbidden()

    product = get_secure_object(Product.objects.all(), request, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f"Product '{name}' archived (removed from lists).")

    if request.headers.get("HX-Request"):
        return HttpResponse(status=200)
    return redirect("products:list")
