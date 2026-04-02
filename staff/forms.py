from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Staff

User = get_user_model()


class StaffCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=8)
    whatsapp_number = forms.CharField(
        max_length=32,
        label=_("WhatsApp number"),
        help_text=_("Digits only; include country code without + (e.g. 919876543210)."),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(_("A user with this username already exists."))
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("A user with this email already exists."))
        return email

    def clean_whatsapp_number(self):
        raw = (self.cleaned_data.get("whatsapp_number") or "").strip()
        if not raw:
            raise ValidationError(_("WhatsApp number is required."))
        return raw

    def clean(self):
        data = super().clean()
        if data.get("password1") and data.get("password2"):
            if data["password1"] != data["password2"]:
                raise ValidationError(_("Passwords do not match."))
        return data


class StaffEditForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = (
            "whatsapp_number",
            "is_active",
            "can_view_all_collections",
            "can_edit_collection",
            "can_view_reports",
            "can_export_data",
            "can_manage_products",
            "can_manage_categories",
            "can_add_customers",
            "can_edit_customers",
        )
