from __future__ import annotations

from functools import wraps

from django.http import HttpResponseForbidden


def _role_required(role: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, "user", None)
            if not user or not getattr(user, "is_authenticated", False):
                return HttpResponseForbidden("Authentication required.")
            if getattr(user, "role", None) != role:
                return HttpResponseForbidden("Forbidden.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


admin_required = _role_required("admin")
vendor_required = _role_required("vendor")
staff_required = _role_required("staff")

