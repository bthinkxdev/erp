from __future__ import annotations

import csv
from datetime import date
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from . import services
from staff.models import Staff
from utils.queryset import secure_queryset
from utils.security import (
    log_permission_denied,
    normalized_analytics_staff_id,
    staff_export_allowed,
    staff_reports_allowed,
)
from utils.vendor import get_vendor_from_request


def _require_vendor_context(request):
    """
    Admin can operate without vendor context; vendor/staff must have request.vendor.
    """
    if getattr(request.user, "role", None) == "admin":
        return None
    vendor = getattr(request, "vendor", None)
    if vendor is not None:
        return vendor
    return get_vendor_from_request(request)


def _require_reports(request) -> bool:
    if staff_reports_allowed(request):
        return True
    log_permission_denied(request, "reports access denied", code="reports_forbidden")
    return False


@login_required
@require_GET
def dashboard_view(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    context = {
        "vendor": vendor,
        "today": timezone.localdate(),
        "summary": services.get_dashboard_summary(vendor, request),
    }
    return render(request, "reports/dashboard.html", context)


@login_required
@require_GET
def today_collection_htmx(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    today_total = services.get_today_collection(vendor, request)
    return render(
        request,
        "reports/partials/today_collection.html",
        {"vendor": vendor, "today_total": today_total, "today": timezone.localdate()},
    )


@login_required
@require_GET
def weekly_collection_htmx(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    raw_week = request.GET.get("week")
    try:
        week_number = int(raw_week) if raw_week is not None else 1
    except (TypeError, ValueError):
        week_number = 1

    week_total = services.get_week_collection(vendor, week_number, request)
    return render(
        request,
        "reports/partials/weekly_collection.html",
        {"vendor": vendor, "week_total": week_total, "week_number": week_number},
    )


@login_required
@require_GET
def staff_report_htmx(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    staff_rows = services.get_staff_collection(vendor, request)
    return render(
        request,
        "reports/partials/staff_report.html",
        {"vendor": vendor, "staff_rows": staff_rows},
    )


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


@login_required
@require_GET
def analytics_view(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    if not _require_reports(request):
        return HttpResponseForbidden("Reports are not enabled for your account.")

    today = timezone.localdate()
    default_end = today
    default_start = today - timedelta(days=6)

    staff_choices = (
        secure_queryset(Staff.objects.filter(is_active=True), request)
        .filter(vendor=vendor)
        .select_related("user")
        .values("id", "user__username")
        .order_by("user__username")
    )

    context = {
        "vendor": vendor,
        "today": today,
        "default_start": default_start,
        "default_end": default_end,
        "staff_choices": staff_choices,
    }
    return render(request, "reports/analytics.html", context)


@login_required
@require_GET
def date_range_report_htmx(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    if not _require_reports(request):
        return HttpResponseForbidden("Reports are not enabled for your account.")

    start_date = _parse_date(request.GET.get("start"))
    end_date = _parse_date(request.GET.get("end"))
    if not start_date or not end_date:
        return HttpResponseBadRequest("Invalid date range.")

    daily_rows = services.get_daily_analytics(vendor, request, start_date, end_date)
    weekly_rows = services.get_weekly_analytics(vendor, request, start_date, end_date)
    monthly_rows = services.get_monthly_analytics(vendor, request, start_date, end_date)

    return render(
        request,
        "reports/partials/date_range.html",
        {
            "vendor": vendor,
            "start_date": start_date,
            "end_date": end_date,
            "daily_rows": daily_rows,
            "weekly_rows": weekly_rows,
            "monthly_rows": monthly_rows,
        },
    )


@login_required
@require_GET
def staff_analytics_htmx(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    if not _require_reports(request):
        return HttpResponseForbidden("Reports are not enabled for your account.")

    start_date = _parse_date(request.GET.get("start"))
    end_date = _parse_date(request.GET.get("end"))

    raw_staff = request.GET.get("staff")
    try:
        staff_id = int(raw_staff) if raw_staff else None
    except (TypeError, ValueError):
        staff_id = None

    staff_id = normalized_analytics_staff_id(request, staff_id)

    rows = services.get_staff_analytics(vendor, request, start_date, end_date, staff_id=staff_id)
    top_rows = services.get_top_staff(vendor, request, start_date, end_date, staff_id=staff_id, limit=5)

    return render(
        request,
        "reports/partials/staff_analytics.html",
        {
            "vendor": vendor,
            "start_date": start_date,
            "end_date": end_date,
            "staff_id": staff_id,
            "rows": rows,
            "top_rows": top_rows,
        },
    )


@login_required
@require_GET
def customer_analytics_htmx(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    if not _require_reports(request):
        return HttpResponseForbidden("Reports are not enabled for your account.")

    start_date = _parse_date(request.GET.get("start"))
    end_date = _parse_date(request.GET.get("end"))

    rows = services.get_customer_analytics(vendor, request, start_date, end_date)
    return render(
        request,
        "reports/partials/customer_analytics.html",
        {"vendor": vendor, "start_date": start_date, "end_date": end_date, "rows": rows},
    )


@login_required
@require_GET
def export_csv_view(request):
    vendor = _require_vendor_context(request)
    if vendor is None:
        return HttpResponseForbidden("No vendor context.")

    if not staff_export_allowed(request):
        log_permission_denied(request, "csv export denied", code="export_forbidden")
        return HttpResponseForbidden("Export is not enabled for your account.")

    start_date = _parse_date(request.GET.get("start"))
    end_date = _parse_date(request.GET.get("end"))
    if not start_date or not end_date:
        return HttpResponseBadRequest("Invalid date range.")

    qs = services.get_collection_by_date_range(vendor, start_date, end_date, request)

    response = HttpResponse(content_type="text/csv")
    filename = f"collections_{vendor.id}_{start_date.isoformat()}_{end_date.isoformat()}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "id",
            "date",
            "week_number",
            "day_number",
            "amount",
            "staff_username",
            "customer_name",
            "customer_phone",
        ]
    )
    for c in qs:
        writer.writerow(
            [
                c.id,
                c.date.isoformat(),
                c.week_number,
                c.day_number,
                str(c.amount),
                c.staff.user.username,
                c.customer.name,
                c.customer.phone,
            ]
        )
    return response
