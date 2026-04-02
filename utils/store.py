from __future__ import annotations

from django.http import Http404
from django.urls import resolve

from staff.models import Staff
from vendors.models import Vendor

# Session key: { "<vendor_pk>": <staff_pk int>, ... }
PUBLIC_STORE_STAFF_SESSION_KEY = "public_store_staff_by_vendor"


def _persist_staff_session(request, sm: dict) -> None:
    request.session[PUBLIC_STORE_STAFF_SESSION_KEY] = sm
    request.session.modified = True


def _is_store_home_request(request) -> bool:
    try:
        match = resolve(request.path_info)
    except Exception:
        return False
    return match.namespace == "store" and match.url_name == "home"


def resolve_store_context(request, vendor_id):
    """
    Resolve public storefront: vendor and optional staff.

    - ``?staff=<pk>`` (valid, for this vendor) scopes orders to that staff's WhatsApp
      and persists the choice in session for subpages.
    - Store **home** ``/store/<vendor_id>/`` with no ``staff`` query clears that
      persistence (vendor storefront).
    - **Category** (and other) pages without ``staff`` in the URL reuse the last
      valid staff id from session for the same vendor so internal links cannot
      drop the scope by accident.
    - ``?staff=`` (empty) clears persistence and uses vendor WhatsApp.
    - Invalid ``?staff=`` still raises Http404.
    """
    try:
        vendor = Vendor.objects.get(pk=vendor_id, is_active=True)
    except Vendor.DoesNotExist:
        raise Http404("Store not found.")

    vid = str(vendor.pk)
    sm = request.session.get(PUBLIC_STORE_STAFF_SESSION_KEY)
    if not isinstance(sm, dict):
        sm = {}

    raw = request.GET.get("staff")

    # Explicit empty ?staff= → stop using staff for this vendor
    if raw is not None and str(raw).strip() == "":
        sm.pop(vid, None)
        _persist_staff_session(request, sm)
        return vendor, None

    # Non-empty ?staff= → must validate
    if raw is not None and str(raw).strip() != "":
        try:
            staff_id = int(raw)
        except (TypeError, ValueError):
            raise Http404("Invalid store link.")
        staff = (
            Staff.objects.filter(
                pk=staff_id,
                vendor_id=vendor.pk,
                is_active=True,
                deleted_at__isnull=True,
            )
            .select_related("vendor", "user")
            .first()
        )
        if staff is None:
            raise Http404("Store not found.")
        sm[vid] = staff.pk
        _persist_staff_session(request, sm)
        return vendor, staff

    # No staff in query string
    if _is_store_home_request(request):
        sm.pop(vid, None)
        _persist_staff_session(request, sm)
        return vendor, None

    sid = sm.get(vid)
    if sid is None:
        return vendor, None
    staff = (
        Staff.objects.filter(
            pk=int(sid),
            vendor_id=vendor.pk,
            is_active=True,
            deleted_at__isnull=True,
        )
        .select_related("vendor", "user")
        .first()
    )
    if staff is None:
        sm.pop(vid, None)
        _persist_staff_session(request, sm)
    return vendor, staff


def store_staff_query_fragment(staff: Staff | None) -> str:
    """``?staff=<pk>`` or empty string for ``href`` after ``{% url %}``."""
    if staff is None:
        return ""
    return f"?staff={staff.pk}"
