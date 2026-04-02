from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from utils.vendor import get_vendor_from_request
from .forms import VendorSettingsForm

User = get_user_model()


def _require_vendor(request):
    vendor = getattr(request, "vendor", None) or get_vendor_from_request(request)
    if not vendor:
        return None, HttpResponseForbidden()
    if getattr(request.user, "role", None) != User.Roles.VENDOR:
        return None, HttpResponseForbidden()
    if vendor.owner_id != request.user.pk:
        return None, HttpResponseForbidden()
    return vendor, None


@login_required
@require_http_methods(["GET", "POST"])
def vendor_settings(request):
    vendor, denied = _require_vendor(request)
    if denied:
        return denied

    if request.method == "POST":
        form = VendorSettingsForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, "Business settings saved.")
            return redirect("vendors:settings")
    else:
        form = VendorSettingsForm(instance=vendor)

    return render(
        request,
        "vendors/settings.html",
        {
            "form": form,
            "vendor": vendor,
        },
    )
