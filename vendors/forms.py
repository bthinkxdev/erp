from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Vendor


class VendorSettingsForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ("name", "whatsapp_number", "staff_see_all_customers")
        labels = {
            "name": _("Business name"),
            "whatsapp_number": _("WhatsApp number"),
            "staff_see_all_customers": _("Staff customer visibility"),
        }

    def clean_whatsapp_number(self):
        raw = (self.cleaned_data.get("whatsapp_number") or "").strip()
        if not raw:
            raise forms.ValidationError(_("WhatsApp number is required."))
        return raw

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError(_("Business name is required."))
        return name
