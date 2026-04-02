from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from vendors.models import VendorAwareModel


class Collection(VendorAwareModel):
    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.PROTECT,
        related_name="collections",
        db_index=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="collections",
        db_index=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    remark = models.TextField(blank=True)
    day_number = models.PositiveIntegerField()
    week_number = models.PositiveIntegerField(db_index=True)
    date = models.DateField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=("vendor", "date"), name="idx_coll_vendor_date"),
            models.Index(fields=("vendor", "staff", "date"), name="idx_coll_vendor_staff_date"),
            models.Index(
                fields=("vendor", "customer", "date"), name="idx_coll_vendor_customer_date"
            ),
            models.Index(fields=("vendor", "week_number"), name="idx_coll_vendor_week"),
        ]

    def clean(self):
        super().clean()

        if self.vendor_id is None or self.staff_id is None or self.customer_id is None:
            return

        if getattr(self.staff, "vendor_id", None) != self.vendor_id:
            raise ValidationError({"staff": _("Staff must belong to the same vendor as this collection.")})

        if getattr(self.customer, "vendor_id", None) != self.vendor_id:
            raise ValidationError(
                {"customer": _("Customer must belong to the same vendor as this collection.")}
            )

        if (
            self.customer_id
            and self.staff_id
            and getattr(self.customer, "staff_id", None)
            and self.customer.staff_id != self.staff_id
        ):
            raise ValidationError(
                {"customer": _("Customer is linked to a different staff member.")}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

