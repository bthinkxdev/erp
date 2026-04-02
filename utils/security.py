from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404

from erp_collections.models import Collection
from users.models import User
from utils.queryset import secure_queryset

logger = logging.getLogger("security.access")


def log_permission_denied(request, message: str, *, code: str = "denied", extra=None) -> None:
    user = getattr(request, "user", None)
    uid = getattr(user, "pk", None)
    uname = getattr(user, "username", "")
    vendor_id = getattr(getattr(request, "vendor", None), "pk", None)
    logger.warning(
        "permission_denied %s user=%s id=%s vendor=%s path=%s",
        code,
        uname,
        uid,
        vendor_id,
        getattr(request, "path", ""),
        extra=extra or {},
    )


def get_secure_object(queryset, request, **kwargs):
    """
    get_object_or_404 on top of secure_queryset (tenant + staff scoping).
    """
    return get_object_or_404(secure_queryset(queryset, request), **kwargs)


def vendor_may_soft_delete(request) -> bool:
    """
    Soft-delete (archive) tenant-owned rows: vendor owners and admins only.
    Staff must never delete records in the ERP UI/API.
    """
    role = getattr(getattr(request, "user", None), "role", None)
    return role in (User.Roles.VENDOR, User.Roles.ADMIN)


def collection_mutation_allowed(request, collection: Collection) -> bool:
    """
    Who may open the collection edit form or POST changes.
    Vendor/admin: always. Staff: own collections always; others only with can_edit_collection.
    """
    user = request.user
    role = getattr(user, "role", None)
    if role == User.Roles.ADMIN:
        return True
    if role == User.Roles.VENDOR:
        return True
    if role == User.Roles.STAFF:
        sp = user.staff_profile
        if sp is None:
            return False
        if collection.staff_id == sp.pk:
            return True
        return bool(sp.can_edit_collection)
    return False


def staff_reports_allowed(request) -> bool:
    user = request.user
    if getattr(user, "role", None) != User.Roles.STAFF:
        return True
    sp = user.staff_profile
    return sp is not None and sp.can_view_reports


def staff_export_allowed(request) -> bool:
    user = request.user
    if getattr(user, "role", None) != User.Roles.STAFF:
        return True
    sp = user.staff_profile
    return sp is not None and sp.can_export_data


def staff_product_mutation_allowed(request) -> bool:
    """Vendor/admin: full access. Staff: needs can_manage_products on profile."""
    user = request.user
    role = getattr(user, "role", None)
    if role == User.Roles.ADMIN:
        return True
    if role == User.Roles.VENDOR:
        return True
    if role == User.Roles.STAFF:
        sp = user.staff_profile
        return sp is not None and sp.can_manage_products
    return False


def staff_category_mutation_allowed(request) -> bool:
    """Vendor/admin: full access. Staff: needs can_manage_categories on profile."""
    user = request.user
    role = getattr(user, "role", None)
    if role == User.Roles.ADMIN:
        return True
    if role == User.Roles.VENDOR:
        return True
    if role == User.Roles.STAFF:
        sp = user.staff_profile
        return sp is not None and sp.can_manage_categories
    return False


def staff_customer_add_allowed(request) -> bool:
    """Vendor/admin: full access. Staff: needs can_add_customers on profile."""
    user = request.user
    role = getattr(user, "role", None)
    if role == User.Roles.ADMIN:
        return True
    if role == User.Roles.VENDOR:
        return True
    if role == User.Roles.STAFF:
        sp = user.staff_profile
        return sp is not None and sp.can_add_customers
    return False


def staff_customer_edit_allowed(request) -> bool:
    """Vendor/admin: full access. Staff: needs can_edit_customers on profile."""
    user = request.user
    role = getattr(user, "role", None)
    if role == User.Roles.ADMIN:
        return True
    if role == User.Roles.VENDOR:
        return True
    if role == User.Roles.STAFF:
        sp = user.staff_profile
        return sp is not None and sp.can_edit_customers
    return False


def normalized_collection_staff_filter(request, raw_staff_id: str | None) -> str | None:
    """
    Prevent staff from filtering collections by another staff's id unless allowed.
    """
    user = request.user
    if getattr(user, "role", None) != User.Roles.STAFF:
        return raw_staff_id
    sp = user.staff_profile
    if sp is None:
        return None
    if sp.can_view_all_collections:
        return raw_staff_id
    return str(sp.pk)


def normalized_analytics_staff_id(request, raw_staff_id: int | None) -> int | None:
    user = request.user
    if getattr(user, "role", None) != User.Roles.STAFF:
        return raw_staff_id
    sp = user.staff_profile
    if sp is None:
        return None
    if sp.can_view_all_collections:
        return raw_staff_id
    if raw_staff_id is not None and raw_staff_id != sp.pk:
        log_permission_denied(
            request,
            "staff analytics scope downgrade",
            code="staff_filter_clamp",
            extra={"requested": raw_staff_id, "forced": sp.pk},
        )
    return sp.pk
