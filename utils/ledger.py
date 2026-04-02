from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from erp_collections.forms import LedgerCollectionForm
from erp_collections.models import Collection
from staff.models import Staff
from users.models import User
from utils.queryset import secure_queryset


def iso_week_and_day() -> tuple[int, int]:
    today = date.today()
    _y, week, weekday = today.isocalendar()
    return week, int(weekday)


def acting_staff_for_collection(request, customer):
    user = request.user
    role = getattr(user, "role", None)
    vendor = customer.vendor

    if role == User.Roles.STAFF:
        sp = user.staff_profile
        if sp is None or sp.vendor_id != vendor.pk:
            return None
        return sp

    if role == User.Roles.VENDOR:
        if customer.staff_id:
            return customer.staff
        qs = secure_queryset(Staff.objects.filter(is_active=True), request).filter(vendor=vendor)
        return qs.order_by("id").first()

    if role == User.Roles.ADMIN:
        if customer.staff_id:
            return customer.staff
        return Staff.objects.filter(vendor=vendor, is_active=True).order_by("id").first()

    return None


def ledger_context(
    customer,
    request,
    ledger_form=None,
    *,
    collection_saved: bool = False,
    ledger_collect_url: str = "",
    ledger_panel_selector: str = "#ledger-modal-panel",
):
    cols = (
        secure_queryset(Collection.objects.filter(customer=customer), request)
        .select_related("staff__user")
        .order_by("-date", "-id")
    )
    agg = cols.aggregate(total=Sum("amount"))
    total_paid = agg["total"] or Decimal("0")
    balance = customer.loan_amount - total_paid
    return {
        "customer": customer,
        "collections": cols,
        "total_paid": total_paid,
        "balance": balance,
        "ledger_form": ledger_form if ledger_form is not None else LedgerCollectionForm(),
        "collection_saved": collection_saved,
        "ledger_collect_url": ledger_collect_url,
        "ledger_panel_selector": ledger_panel_selector,
    }


def process_ledger_collect_post(request, customer, vendor):
    form = LedgerCollectionForm(request.POST)
    if not form.is_valid():
        return form, None, False

    staff = acting_staff_for_collection(request, customer)
    if staff is None:
        form.add_error(None, "No staff member could be assigned for this collection.")
        return form, None, False

    week_no, day_no = iso_week_and_day()
    col = Collection(
        vendor=vendor,
        staff=staff,
        customer=customer,
        amount=form.cleaned_data["amount"],
        remark=form.cleaned_data.get("remark") or "",
        week_number=week_no,
        day_number=day_no,
    )
    try:
        col.save()
    except ValidationError as exc:
        msgs = getattr(exc, "messages", None)
        err_txt = " ".join(msgs) if msgs else str(exc)
        form.add_error(None, err_txt)
        return form, None, False

    return None, col, True
