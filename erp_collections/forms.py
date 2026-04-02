from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from users.models import User

from .models import Collection


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ("customer", "staff", "amount", "week_number", "day_number", "remark")
        widgets = {
            "remark": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, vendor=None, request=None, **kwargs):
        self._request = request
        self._vendor = vendor
        super().__init__(*args, **kwargs)

        if not vendor:
            return

        from customers.models import Customer
        from staff.models import Staff

        acting_staff = None
        if request and request.user.is_authenticated:
            if getattr(request.user, "role", None) == User.Roles.STAFF:
                acting_staff = request.user.staff_profile

        if acting_staff:
            if getattr(vendor, "staff_see_all_customers", False):
                self.fields["customer"].queryset = Customer.objects.filter(vendor=vendor).order_by(
                    "name"
                )
            else:
                q = Q(staff=acting_staff)
                if self.instance and self.instance.pk and self.instance.customer_id:
                    q |= Q(pk=self.instance.customer_id)
                self.fields["customer"].queryset = (
                    Customer.objects.filter(vendor=vendor).filter(q).order_by("name")
                )
            self.fields.pop("staff", None)
        else:
            self.fields["customer"].queryset = Customer.objects.filter(vendor=vendor).order_by(
                "name"
            )
            self.fields["staff"].queryset = (
                Staff.objects.filter(vendor=vendor, is_active=True)
                .select_related("user")
                .order_by("user__username")
            )

    def clean(self):
        cleaned = super().clean()
        req = self._request
        if not req or not req.user.is_authenticated:
            return cleaned

        if getattr(req.user, "role", None) != User.Roles.STAFF:
            return cleaned

        sp = req.user.staff_profile
        if sp is None:
            raise ValidationError(_("Invalid staff session."))

        if "staff" in self.fields:
            st = cleaned.get("staff")
            if st is not None and st.pk != sp.pk:
                raise ValidationError({"staff": _("You can only record collections for yourself.")})

        cust = cleaned.get("customer")
        if (
            cust is not None
            and cust.staff_id
            and cust.staff_id != sp.pk
            and not getattr(self._vendor, "staff_see_all_customers", False)
        ):
            raise ValidationError({"customer": _("This customer is not assigned to you.")})

        return cleaned


class LedgerCollectionForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    remark = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise ValidationError(_("Amount must be greater than zero."))
        return amount
