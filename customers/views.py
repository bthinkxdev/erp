from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError as DjangoValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from users.models import User

from utils.htmx import is_hx_swap_into
from utils.ledger import ledger_context, process_ledger_collect_post
from utils.queryset import secure_queryset
from utils.security import (
    get_secure_object,
    staff_customer_add_allowed,
    staff_customer_edit_allowed,
    vendor_may_soft_delete,
)
from utils.vendor import get_vendor_from_request
from .forms import CustomerForm
from .models import Customer


def _vendor(request):
    vendor = getattr(request, "vendor", None)
    return vendor or get_vendor_from_request(request)


def _save_customer_or_add_form_errors(form, customer) -> bool:
    """Returns True if save succeeded. On model ValidationError, attaches errors to form and returns False."""
    try:
        customer.save()
    except DjangoValidationError as exc:
        if hasattr(exc, "error_dict"):
            for field, error_list in exc.error_dict.items():
                target = None if field == NON_FIELD_ERRORS else field
                for err in error_list:
                    form.add_error(target, err)
        else:
            form.add_error(None, " ".join(str(m) for m in exc.messages))
        return False
    return True


def _handle_customer_photo_side_effects(
    *,
    form: CustomerForm,
    customer: Customer,
    previous_photo,
) -> None:
    """
    Applies photo removal / old-file cleanup after a successful save.
    Keeps the "what file to keep" logic in one place to avoid double-saving the instance.
    """
    remove_photo = bool(getattr(form, "cleaned_data", {}).get("remove_photo"))
    old_photo = previous_photo
    new_photo = getattr(customer, "photo", None)

    if remove_photo:
        if old_photo:
            old_photo.delete(save=False)
        if new_photo and (not old_photo or new_photo.name != old_photo.name):
            new_photo.delete(save=False)
        customer.photo = None
        customer.save(update_fields=["photo"])
        return

    if old_photo and new_photo and old_photo.name != new_photo.name:
        old_photo.delete(save=False)


@login_required
def customer_list(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()

    qs = secure_queryset(Customer.objects.all(), request)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(customer_code__icontains=q) | Q(phone__icontains=q))

    sort = request.GET.get("sort", "").strip()
    order = request.GET.get("order", "desc")
    if sort in ("name", "phone"):
        qs = qs.order_by(f"{'-' if order == 'desc' else ''}{sort}")
    else:
        qs = qs.order_by("-created_at", "-id")

    total_count = qs.count()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    if is_hx_swap_into(request, "customer-results"):
        return render(request, "customers/_results.html", {
            "customers": page_obj.object_list,
            "offset": (page_obj.number - 1) * paginator.per_page,
        })

    return render(
        request,
        "customers/list.html",
        {
            "customers": page_obj.object_list,
            "page_obj": page_obj,
            "total_count": total_count,
            "offset": 0,
            "vendor": vendor,
        },
    )


@login_required
@require_POST
def toggle_staff_customer_scope(request):
    vendor = _vendor(request)
    if not vendor or getattr(request.user, "role", None) != User.Roles.VENDOR:
        return HttpResponseForbidden()

    vendor.staff_see_all_customers = request.POST.get("staff_see_all_customers") == "on"
    vendor.save(update_fields=["staff_see_all_customers"])
    if vendor.staff_see_all_customers:
        messages.success(
            request,
            "All staff can now see every customer for your business.",
        )
    else:
        messages.success(
            request,
            "Staff will only see customers assigned to them.",
        )
    return redirect("customers:list")


@login_required
@require_http_methods(["GET", "POST"])
def customer_add(request):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not staff_customer_add_allowed(request):
        return HttpResponseForbidden()

    if request.method == "POST":
        form = CustomerForm(request.POST, request.FILES, vendor=vendor, request=request)
        if form.is_valid():
            previous_photo = None
            customer = form.save(commit=False)
            customer.vendor = vendor
            if getattr(request.user, "role", None) == User.Roles.STAFF:
                if not vendor.staff_see_all_customers:
                    customer.staff = request.user.staff_profile
            if not _save_customer_or_add_form_errors(form, customer):
                return render(request, "customers/form.html", {"form": form})
            _handle_customer_photo_side_effects(form=form, customer=customer, previous_photo=previous_photo)
            messages.success(request, f"Customer '{customer.name}' added.")
            return redirect("customers:list")
    else:
        form = CustomerForm(vendor=vendor, request=request)

    return render(request, "customers/form.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def customer_edit(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not staff_customer_edit_allowed(request):
        return HttpResponseForbidden()

    customer = get_secure_object(Customer.objects.all(), request, pk=pk)

    if request.method == "POST":
        previous_photo = customer.photo
        form = CustomerForm(request.POST, request.FILES, instance=customer, vendor=vendor, request=request)
        if form.is_valid():
            customer = form.save(commit=False)
            if getattr(request.user, "role", None) == User.Roles.STAFF:
                if not vendor.staff_see_all_customers:
                    customer.staff = request.user.staff_profile
            if not _save_customer_or_add_form_errors(form, customer):
                return render(request, "customers/form.html", {"form": form})
            _handle_customer_photo_side_effects(form=form, customer=customer, previous_photo=previous_photo)
            messages.success(request, f"Customer '{customer.name}' updated.")
            return redirect("customers:list")
    else:
        form = CustomerForm(instance=customer, vendor=vendor, request=request)

    return render(request, "customers/form.html", {"form": form})


@login_required
@require_http_methods(["POST", "DELETE"])
def customer_delete(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()
    if not vendor_may_soft_delete(request):
        return HttpResponseForbidden()

    customer = get_secure_object(Customer.objects.all(), request, pk=pk)
    name = customer.name
    customer.delete()
    messages.success(request, f"Customer '{name}' archived (removed from lists).")

    if request.headers.get("HX-Request"):
        return HttpResponse(status=200)
    return redirect("customers:list")


@login_required
@require_GET
def customer_ledger_modal(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()

    customer = get_secure_object(
        Customer.objects.select_related("vendor", "staff__user"),
        request,
        pk=pk,
    )
    collect_url = reverse("customers:ledger_collect", kwargs={"pk": customer.pk})
    ctx = ledger_context(
        customer,
        request,
        ledger_collect_url=collect_url,
        ledger_panel_selector="#modal-body",
    )
    ctx["dismiss_url"] = reverse("customers:ledger_dismiss")
    ctx["host_selector"] = "#customer-ledger-modal-host"
    ctx["modal_title"] = (
        f"Ledger — {customer.name} ({customer.customer_code})"
        if customer.customer_code
        else f"Ledger — {customer.name}"
    )
    return render(request, "customers/partials/ledger_modal.html", ctx)


@login_required
@require_GET
def customer_ledger_dismiss(request):
    return HttpResponse("")


@login_required
@require_http_methods(["POST"])
def customer_ledger_collect(request, pk):
    vendor = _vendor(request)
    if not vendor:
        return HttpResponseForbidden()

    customer = get_secure_object(Customer.objects.all(), request, pk=pk)
    collect_url = reverse("customers:ledger_collect", kwargs={"pk": customer.pk})

    form, _col, ok = process_ledger_collect_post(request, customer, vendor)
    if form is not None:
        ctx = ledger_context(
            customer,
            request,
            ledger_form=form,
            ledger_collect_url=collect_url,
            ledger_panel_selector="#modal-body",
        )
        return render(request, "collections/partials/ledger_panel.html", ctx)

    ctx = ledger_context(
        customer,
        request,
        collection_saved=ok,
        ledger_collect_url=collect_url,
        ledger_panel_selector="#modal-body",
    )
    return render(request, "collections/partials/ledger_panel.html", ctx)
