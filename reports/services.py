from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from erp_collections.models import Collection
from staff.models import Staff
from customers.models import Customer
from users.models import User
from utils.queryset import secure_queryset

__all__ = (
    "get_today_collection",
    "get_week_collection",
    "get_staff_collection",
    "get_dashboard_summary",
    "get_collection_by_date_range",
    "get_daily_analytics",
    "get_weekly_analytics",
    "get_monthly_analytics",
    "get_staff_analytics",
    "get_top_staff",
    "get_customer_analytics",
)


def _collections(request, vendor, **filters):
    qs = secure_queryset(Collection.objects.all(), request).filter(vendor=vendor, **filters)
    return qs


def get_today_collection(vendor, request) -> Decimal:
    today = timezone.localdate()
    result = _collections(request, vendor, date=today).aggregate(total=Sum("amount"))
    return result["total"] or Decimal("0.00")


def get_week_collection(vendor, week_number: int, request) -> Decimal:
    result = _collections(request, vendor, week_number=week_number).aggregate(total=Sum("amount"))
    return result["total"] or Decimal("0.00")


def get_staff_collection(vendor, request):
    """
    Staff-wise performance within a vendor (scoped to request).
    """
    user = getattr(request, "user", None)
    if user and getattr(user, "role", None) == User.Roles.STAFF:
        sp = user.staff_profile
        if sp is None or not sp.can_view_reports:
            return []

    return (
        _collections(request, vendor)
        .select_related("staff__user")
        .values("staff__user__username")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )


def get_dashboard_summary(vendor, request) -> dict[str, Any]:
    scoped = _collections(request, vendor)
    total_collection = scoped.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    today = timezone.localdate()
    today_collection = scoped.filter(date=today).aggregate(total=Sum("amount"))["total"] or Decimal(
        "0.00"
    )
    total_customers = secure_queryset(Customer.objects.all(), request).filter(vendor=vendor).count()
    total_staff = secure_queryset(Staff.objects.all(), request).filter(
        vendor=vendor, is_active=True
    ).count()

    return {
        "total_collection": total_collection,
        "today_collection": today_collection,
        "total_customers": total_customers,
        "total_staff": total_staff,
    }


def get_collection_by_date_range(vendor, start_date, end_date, request):
    return (
        _collections(request, vendor, date__range=[start_date, end_date])
        .select_related("staff__user", "customer")
        .order_by("date", "id")
    )


def get_daily_analytics(vendor, request, start_date=None, end_date=None):
    qs = _collections(request, vendor)
    if start_date and end_date:
        qs = qs.filter(date__range=[start_date, end_date])
    return qs.values("date").annotate(total=Sum("amount")).order_by("date")


def get_weekly_analytics(vendor, request, start_date=None, end_date=None):
    qs = _collections(request, vendor)
    if start_date and end_date:
        qs = qs.filter(date__range=[start_date, end_date])
    return qs.values("week_number").annotate(total=Sum("amount")).order_by("week_number")


def get_monthly_analytics(vendor, request, start_date=None, end_date=None):
    qs = _collections(request, vendor)
    if start_date and end_date:
        qs = qs.filter(date__range=[start_date, end_date])
    from django.db.models.functions import TruncMonth

    return (
        qs.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )


def get_staff_analytics(vendor, request, start_date=None, end_date=None, staff_id: int | None = None):
    qs = _collections(request, vendor).select_related("staff__user")
    if start_date and end_date:
        qs = qs.filter(date__range=[start_date, end_date])
    if staff_id:
        qs = qs.filter(staff_id=staff_id)
    return (
        qs.values("staff_id", "staff__user__username")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )


def get_top_staff(vendor, request, start_date=None, end_date=None, staff_id: int | None = None, limit: int = 5):
    return get_staff_analytics(vendor, request, start_date, end_date, staff_id=staff_id).order_by("-total")[
        :limit
    ]


def get_customer_analytics(vendor, request, start_date=None, end_date=None):
    user = getattr(request, "user", None)
    if user and getattr(user, "role", None) == User.Roles.STAFF:
        sp = user.staff_profile
        if sp is None or not sp.can_view_reports:
            return []

    qs = _collections(request, vendor).select_related("customer")
    if start_date and end_date:
        qs = qs.filter(date__range=[start_date, end_date])
    return (
        qs.values("customer_id", "customer__name", "customer__phone")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
