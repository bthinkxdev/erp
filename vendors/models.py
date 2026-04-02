from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import BaseModel


class VendorAwareQuerySet(models.QuerySet):
    """Bulk soft-delete for tenant-scoped rows."""

    def delete(self):
        if not self.exists():
            return 0, {}
        n = self.update(deleted_at=timezone.now())
        counter = defaultdict(int)
        counter[self.model._meta.label] += n
        return n, dict(counter)


class VendorAwareManager(models.Manager):
    def get_queryset(self):
        return VendorAwareQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class Vendor(BaseModel):
    name = models.CharField(max_length=255, db_index=True)
    whatsapp_number = models.CharField(
        _("WhatsApp number"),
        max_length=32,
        db_index=True,
        help_text=_("Business WhatsApp number (digits; include country code without +, e.g. 919876543210)."),
    )
    owner = models.OneToOneField(
        "users.User",
        on_delete=models.PROTECT,
        related_name="vendor",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    staff_see_all_customers = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_(
            "When enabled, all staff in this vendor see every customer. "
            "When disabled, each staff member only sees customers assigned to them."
        ),
    )

    def clean(self):
        super().clean()
        if self.owner_id is None:
            return
        if getattr(self.owner, "role", None) != "vendor":
            raise ValidationError({"owner": _("Owner must be a user with role='vendor'.")})

    def __str__(self) -> str:
        return self.name


class VendorAwareModel(BaseModel):
    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        db_index=True,
    )
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False, db_index=True)

    objects = VendorAwareManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        if self.deleted_at is not None:
            return
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
