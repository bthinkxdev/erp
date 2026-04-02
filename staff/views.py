from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from erp_collections.models import Collection
from utils.htmx import is_hx_swap_into
from utils.queryset import secure_queryset
from utils.security import get_secure_object
from utils.vendor import get_vendor_from_request
from .forms import StaffCreateForm, StaffEditForm
from .models import Staff

User = get_user_model()


def _vendor(request):
    vendor = getattr(request, "vendor", None)
    return vendor or get_vendor_from_request(request)


def _vendor_owner(request):
    """Vendor UI staff management is limited to vendor (owner) accounts."""
    vendor = _vendor(request)
    if not vendor:
        return None, HttpResponseForbidden()
    if getattr(request.user, "role", None) != User.Roles.VENDOR:
        return None, HttpResponseForbidden()
    return vendor, None


@login_required
def staff_list(request):
    vendor, denied = _vendor_owner(request)
    if denied:
        return denied

    qs = secure_queryset(Staff.objects.all(), request).select_related("user").order_by("user__username")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(user__username__icontains=q) | Q(user__email__icontains=q)
        )

    total_count = qs.count()
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    if is_hx_swap_into(request, "staff-table-body"):
        return render(
            request,
            "staff/_rows.html",
            {
                "staff_members": page_obj.object_list,
                "offset": (page_obj.number - 1) * paginator.per_page,
            },
        )

    return render(
        request,
        "staff/list.html",
        {
            "staff_members": page_obj.object_list,
            "page_obj": page_obj,
            "total_count": total_count,
            "offset": 0,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def staff_add(request):
    vendor, denied = _vendor_owner(request)
    if denied:
        return denied

    if request.method == "POST":
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = User.objects.create_user(
                username=cd["username"],
                email=cd["email"],
                password=cd["password1"],
                role=User.Roles.STAFF,
            )
            staff = Staff(user=user, vendor=vendor, whatsapp_number=cd["whatsapp_number"])
            staff.save()
            messages.success(request, f"Staff member '{user.get_username()}' added.")
            return redirect("staff:list")
    else:
        form = StaffCreateForm()

    return render(request, "staff/form_create.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def staff_edit(request, pk):
    vendor, denied = _vendor_owner(request)
    if denied:
        return denied

    staff = get_secure_object(Staff.objects.select_related("user"), request, pk=pk)

    if request.method == "POST":
        form = StaffEditForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Staff member '{staff.user.get_username()}' updated.",
            )
            return redirect("staff:list")
    else:
        form = StaffEditForm(instance=staff)

    store_path = reverse("store:home", kwargs={"vendor_id": vendor.pk})
    staff_store_share_url = request.build_absolute_uri(f"{store_path}?staff={staff.pk}")

    return render(
        request,
        "staff/form_edit.html",
        {
            "form": form,
            "staff_member": staff,
            "staff_store_share_url": staff_store_share_url,
        },
    )


@login_required
@require_http_methods(["POST", "DELETE"])
def staff_delete(request, pk):
    vendor, denied = _vendor_owner(request)
    if denied:
        return denied

    staff = get_secure_object(Staff.objects.select_related("user"), request, pk=pk)
    if staff.user_id == vendor.owner_id:
        messages.error(request, "Cannot remove the vendor owner account.")
        if request.headers.get("HX-Request"):
            return HttpResponse(status=400)
        return redirect("staff:list")

    username = staff.user.get_username()
    staff.delete()
    messages.success(request, f"Staff member '{username}' archived and sign-in disabled.")

    if request.headers.get("HX-Request"):
        return HttpResponse(status=200)
    return redirect("staff:list")


def _parse_ledger_date(raw: str | None, default: date) -> date:
    if not raw:
        return default
    try:
        y, m, d = (int(p) for p in raw.split("-", 2))
        return date(y, m, d)
    except (ValueError, TypeError):
        return default


@login_required
@require_GET
def vendor_collections_ledger_modal(request):
    vendor, denied = _vendor_owner(request)
    if denied:
        return denied

    today = date.today()
    month_start = today.replace(day=1)

    date_from = _parse_ledger_date(request.GET.get("date_from"), month_start)
    date_to = _parse_ledger_date(request.GET.get("date_to"), today)
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    staff_selected: int | None = None
    raw_staff = request.GET.get("staff", "").strip()
    if raw_staff:
        try:
            staff_selected = int(raw_staff)
        except ValueError:
            staff_selected = None

    qs = (
        secure_queryset(Collection.objects.all(), request)
        .filter(date__gte=date_from, date__lte=date_to)
        .select_related("customer", "staff__user")
        .order_by("-date", "-pk")
    )

    if staff_selected is not None:
        get_secure_object(Staff.objects.all(), request, pk=staff_selected)
        qs = qs.filter(staff_id=staff_selected)

    total_amount = qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    total_count = qs.count()

    paginator = Paginator(qs, 40)
    page_obj = paginator.get_page(request.GET.get("page"))

    staff_choices = list(
        secure_queryset(Staff.objects.filter(is_active=True), request)
        .select_related("user")
        .order_by("user__username")
    )

    title_staff = None
    if staff_selected is not None:
        title_staff = next((s for s in staff_choices if s.pk == staff_selected), None)

    modal_title = "Collection ledger"
    if title_staff is not None:
        modal_title = f"Collection ledger — {title_staff.user.get_username()}"

    ctx = {
        "modal_title": modal_title,
        "dismiss_url": reverse("staff:collections_ledger_dismiss"),
        "host_selector": "#staff-ledger-modal-host",
        "date_from": date_from,
        "date_to": date_to,
        "staff_selected": staff_selected,
        "staff_choices": staff_choices,
        "collections": page_obj.object_list,
        "page_obj": page_obj,
        "total_amount": total_amount,
        "total_count": total_count,
    }
    return render(request, "staff/partials/collections_ledger_modal.html", ctx)


@login_required
@require_GET
def vendor_collections_ledger_dismiss(request):
    vendor, denied = _vendor_owner(request)
    if denied:
        return denied
    return HttpResponse("")
