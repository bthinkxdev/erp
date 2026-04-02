from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from customers.models import Customer
from staff.models import Staff
from users.models import User
from utils.htmx import is_hx_swap_into
from utils.ledger import ledger_context, process_ledger_collect_post
from utils.queryset import secure_queryset
from utils.security import (
    collection_mutation_allowed,
    get_secure_object,
    log_permission_denied,
    normalized_collection_staff_filter,
)
from utils.vendor import get_vendor_from_request

from .forms import CollectionForm
from .models import Collection


def _vendor(request):
    return getattr(request, "vendor", None) or get_vendor_from_request(request)


@login_required
def day_dashboard(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()

    return render(
        request,
        "collections/day_dashboard.html",
        {
            "day_choices": range(1, 8),
        },
    )


@login_required
@require_GET
def get_customers_by_day_htmx(request, day: int):
    from decimal import Decimal

    from django.db.models import Sum

    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if day < 1 or day > 7:
        return HttpResponseBadRequest("Day must be 1–7.")

    qs = (
        secure_queryset(Customer.objects.all(), request)
        .filter(vendor=vendor, assigned_day=day)
        .select_related("staff__user")
        .order_by("-created_at", "-id")
    )
    customers = list(qs)
    if customers:
        paid_rows = (
            secure_queryset(Collection.objects.all(), request)
            .filter(customer_id__in=[c.pk for c in customers])
            .values("customer_id")
            .annotate(total=Sum("amount"))
        )
        paid_map = {row["customer_id"]: row["total"] or Decimal("0") for row in paid_rows}
        for c in customers:
            paid = paid_map.get(c.pk, Decimal("0"))
            setattr(c, "ledger_paid", paid)
            setattr(c, "ledger_balance", c.loan_amount - paid)

    return render(
        request,
        "collections/partials/customer_list.html",
        {
            "customers": customers,
            "day": day,
        },
    )


@login_required
def collection_list(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()

    qs = (
        secure_queryset(Collection.objects.all(), request)
        .select_related("customer", "staff__user")
        .order_by("-date", "-pk")
    )

    staff_filter = normalized_collection_staff_filter(request, request.GET.get("staff"))
    if request.GET.get("date"):
        qs = qs.filter(date=request.GET["date"])
    if staff_filter:
        qs = qs.filter(staff_id=staff_filter)
    if request.GET.get("week"):
        qs = qs.filter(week_number=request.GET["week"])

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(customer__name__icontains=q) | Q(customer__customer_code__icontains=q))

    total_count = qs.count()
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get("page"))

    staff_choices = (
        secure_queryset(Staff.objects.filter(is_active=True), request)
        .filter(vendor=vendor)
        .select_related("user")
        .values("id", "user__username")
        .order_by("user__username")
    )

    if is_hx_swap_into(request, "collection-table-body"):
        return render(
            request,
            "erp_collections/_rows.html",
            {
                "collections": page_obj.object_list,
            },
        )

    return render(
        request,
        "erp_collections/list.html",
        {
            "collections": page_obj.object_list,
            "page_obj": page_obj,
            "total_count": total_count,
            "staff_choices": staff_choices,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def collection_add(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()

    if getattr(request.user, "role", None) == User.Roles.STAFF and request.user.staff_profile is None:
        return HttpResponseForbidden()

    if request.method == "POST":
        form = CollectionForm(request.POST, vendor=vendor, request=request)
        if form.is_valid():
            col = form.save(commit=False)
            col.vendor = vendor
            if getattr(request.user, "role", None) == User.Roles.STAFF:
                col.staff = request.user.staff_profile
            else:
                col.staff = form.cleaned_data["staff"]
            col.save()
            messages.success(request, f"Collection of ₹{col.amount} recorded.")
            return redirect("collections:list")
    else:
        form = CollectionForm(vendor=vendor, request=request)

    return render(request, "erp_collections/form.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def collection_edit(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()

    collection = get_secure_object(
        Collection.objects.select_related("customer", "staff__user"),
        request,
        pk=pk,
    )

    if not collection_mutation_allowed(request, collection):
        log_permission_denied(request, "collection edit denied", code="collection_edit_denied")
        return HttpResponseForbidden("You cannot change this collection.")

    if request.method == "POST":
        form = CollectionForm(
            request.POST,
            instance=collection,
            vendor=vendor,
            request=request,
        )
        if form.is_valid():
            col = form.save(commit=False)
            if getattr(request.user, "role", None) == User.Roles.STAFF:
                col.staff = request.user.staff_profile
            else:
                col.staff = form.cleaned_data["staff"]
            col.save()
            messages.success(request, "Collection updated.")
            return redirect("collections:list")
    else:
        form = CollectionForm(instance=collection, vendor=vendor, request=request)

    return render(request, "erp_collections/form.html", {"form": form})
