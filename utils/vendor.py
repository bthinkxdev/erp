from __future__ import annotations


def get_vendor_from_request(request):
    """
    Resolve vendor context from an authenticated request.

    - vendor user: request.user.vendor_profile
    - staff user: request.user.staff_profile.vendor
    - admin user: None (admin can access all)
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None

    role = getattr(user, "role", None)
    if role == "admin":
        return None
    if role == "vendor":
        return getattr(user, "vendor_profile", None)
    if role == "staff":
        staff = getattr(user, "staff_profile", None)
        return getattr(staff, "vendor", None) if staff is not None else None
    return None

