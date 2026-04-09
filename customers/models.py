from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import IntegrityError, models, transaction
from django.utils.translation import gettext_lazy as _

from vendors.models import Vendor, VendorAwareModel


def _vendor_name_prefix(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return "XX"
    first, last = n[0].upper(), n[-1].upper()
    if not first.isalnum():
        first = "X"
    if not last.isalnum():
        last = "X"
    return (first + last)[:2]


class Customer(VendorAwareModel):
    ASSIGNED_DAY_CHOICES = [(i, f"Day {i}") for i in range(1, 8)]
    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.CASCADE,
        related_name="customers",
        null=True,
        blank=True,
        db_index=True,
    )
    name = models.CharField(max_length=255, db_index=True)
    phone = models.CharField(max_length=32, db_index=True)
    address = models.TextField(blank=True)
    loan_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.01"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    assigned_day = models.IntegerField(choices=ASSIGNED_DAY_CHOICES, default=1, db_index=True)
    customer_code = models.CharField(max_length=10, editable=False)
    photo = models.ImageField(upload_to="customers/", blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("vendor", "phone"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_customer_vendor_phone_active",
            ),
            models.UniqueConstraint(
                fields=("vendor", "customer_code"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_customer_vendor_code_active",
            ),
        ]
        indexes = [
            models.Index(fields=("vendor", "name"), name="idx_customer_vendor_name"),
            models.Index(fields=("vendor", "phone"), name="idx_customer_vendor_phone"),
            models.Index(fields=("vendor", "staff"), name="idx_customer_vendor_staff"),
            models.Index(fields=("vendor", "customer_code"), name="idx_customer_vendor_code"),
        ]

    def clean(self):
        super().clean()
        if self.assigned_day is not None and not (1 <= self.assigned_day <= 7):
            raise ValidationError({"assigned_day": _("Assigned day must be between 1 and 7.")})
        if self.loan_amount is not None and self.loan_amount <= 0:
            raise ValidationError({"loan_amount": _("Loan amount must be greater than zero.")})
        if self.staff_id is None or self.vendor_id is None:
            return
        if getattr(self.staff, "vendor_id", None) != self.vendor_id:
            raise ValidationError({"staff": _("Assigned staff must belong to this vendor.")})

    def _assign_customer_code_locked(self) -> None:
        prefix = _vendor_name_prefix(self.vendor.name)
        last = (
            Customer.objects.filter(vendor_id=self.vendor_id)
            .order_by("-id")
            .first()
        )
        n = 1 if not last else last.id + 1
        candidate = f"{prefix}{n:02d}"[:10]
        while (
            Customer.objects.filter(vendor_id=self.vendor_id, customer_code=candidate)
            .exclude(pk=self.pk)
            .exists()
        ):
            n += 1
            candidate = f"{prefix}{n:02d}"[:10]
        self.customer_code = candidate

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if self.pk and update_fields is not None and "customer_code" not in update_fields:
            self.full_clean()
            return super().save(*args, **kwargs)

        assign_code = bool(self.vendor_id and not self.customer_code)
        if assign_code:
            for attempt in range(12):
                try:
                    with transaction.atomic():
                        Vendor.objects.select_for_update().get(pk=self.vendor_id)
                        self._assign_customer_code_locked()
                        self.full_clean()
                        return super().save(*args, **kwargs)
                except IntegrityError as exc:
                    self.customer_code = ""
                    if self.pk:
                        raise exc
                    if attempt == 11:
                        raise IntegrityError(
                            "Could not allocate a unique customer_code."
                        ) from exc
                    continue
            raise IntegrityError("Could not allocate a unique customer_code.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.customer_code:
            return f"{self.name} ({self.customer_code})"
        return f"{self.name} ({self.phone})"

