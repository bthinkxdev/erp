from __future__ import annotations

from django.core.exceptions import FieldDoesNotExist

from users.models import User


def _request_has_global_data_access(user) -> bool:
    """True for ERP `role=admin` and Django superusers (e.g. createsuperuser default role=staff)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "role", None) == User.Roles.ADMIN:
        return True
    if getattr(user, "is_superuser", False):
        return True
    return False


def _model_has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except FieldDoesNotExist:
        return False


def filter_by_vendor(queryset, request):
    """
    Enforce tenant isolation on a VendorAwareModel queryset.

    - admin: no filtering
    - otherwise: filter(vendor=request.vendor)
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return queryset.none()

    if _request_has_global_data_access(user):
        return queryset

    vendor = getattr(request, "vendor", None)
    if vendor is None:
        return queryset.none()

    return queryset.filter(vendor=vendor)


def secure_queryset(queryset, request):
    """
    Production tenant + staff row-level rules for querysets.

    - Unauthenticated: empty
    - Admin role or Django superuser: unchanged (full data for /admin/)
    - Vendor: filter to own vendor (when model has vendor FK)
    - Staff: filter to vendor + Collection rows limited by can_view_all_collections;
             Staff model limited to own profile

    Preserves filter_by_vendor behaviour for vendor-role users.
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return queryset.none()

    if _request_has_global_data_access(user):
        return queryset

    role = getattr(user, "role", None)

    model = queryset.model
    vendor = getattr(request, "vendor", None)

    from customers.models import Customer
    from erp_collections.models import Collection
    from staff.models import Staff
    from vendors.models import Vendor

    if model is Vendor:
        if vendor is None:
            return queryset.none()
        return queryset.filter(pk=vendor.pk)

    if not _model_has_field(model, "vendor"):
        return queryset.none()

    if vendor is None:
        return queryset.none()

    qs = queryset.filter(vendor=vendor)

    if role == User.Roles.VENDOR:
        return qs

    if role != User.Roles.STAFF:
        return queryset.none()

    staff_profile = user.staff_profile
    if staff_profile is None:
        return queryset.none()

    if model is Staff:
        return qs.filter(pk=staff_profile.pk)

    if model is Customer:
        if getattr(vendor, "staff_see_all_customers", False):
            return qs
        return qs.filter(staff_id=staff_profile.pk)

    if model is Collection:
        if not staff_profile.can_view_all_collections:
            qs = qs.filter(staff_id=staff_profile.pk)

    return qs
