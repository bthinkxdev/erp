from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from users.models import User

from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = (
            "name",
            "phone",
            "address",
            "staff",
            "loan_amount",
            "assigned_day",
            "latitude",
            "longitude",
        )
        widgets = {
            "loan_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "latitude": forms.HiddenInput(attrs={"id": "latitude"}),
            "longitude": forms.HiddenInput(attrs={"id": "longitude"}),
        }

    def __init__(self, *args, vendor=None, request=None, **kwargs):
        self._request = request
        self._vendor = vendor
        super().__init__(*args, **kwargs)

        if "staff" in self.fields:
            self.fields["staff"].required = False

        if request and request.user.is_authenticated:
            if getattr(request.user, "role", None) == User.Roles.STAFF:
                self.fields.pop("staff", None)
            elif vendor is not None and "staff" in self.fields:
                from staff.models import Staff

                self.fields["staff"].queryset = (
                    Staff.objects.filter(vendor=vendor, is_active=True)
                    .select_related("user")
                    .order_by("user__username")
                )

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        return phone

    def clean(self):
        cleaned_data = super().clean()
        vendor = self._vendor
        phone = cleaned_data.get("phone")
        if not vendor or not phone:
            return cleaned_data

        qs = Customer.objects.filter(vendor=vendor, phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                {
                    "phone": _(
                        "A customer with this phone number already exists for your business."
                    ),
                }
            )
        return cleaned_data
