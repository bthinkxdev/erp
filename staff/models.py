from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import User
from vendors.models import VendorAwareManager, VendorAwareModel, VendorAwareQuerySet


class StaffQuerySet(VendorAwareQuerySet):
    def delete(self):
        if not self.exists():
            return 0, {}
        now = timezone.now()
        user_ids = list(self.values_list("user_id", flat=True))
        n = self.update(deleted_at=now, is_active=False)
        if user_ids:
            User.objects.filter(pk__in=user_ids).update(is_active=False)
        counter = defaultdict(int)
        counter[self.model._meta.label] += n
        return n, dict(counter)


class StaffManager(VendorAwareManager):
    def get_queryset(self):
        return StaffQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class Staff(VendorAwareModel):
    objects = StaffManager()
    all_objects = models.Manager()

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="staff",
    )
    whatsapp_number = models.CharField(
        _("WhatsApp number"),
        max_length=32,
        db_index=True,
        help_text=_("WhatsApp number for this team member (digits; include country code without +)."),
    )
    is_active = models.BooleanField(default=True, db_index=True)

    can_view_all_collections = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("See all collections for this vendor (not only own)."),
    )
    can_edit_collection = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Create/edit collections on behalf of any staff member in this vendor."),
    )
    can_view_reports = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Access analytics and staff breakdown reports."),
    )
    can_export_data = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Download CSV exports."),
    )
    can_manage_products = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Add, edit, and delete products for this vendor."),
    )
    can_manage_categories = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Add, edit, and delete product categories (manage categories modal)."),
    )
    can_add_customers = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Create new customers (subject to customer visibility rules for this vendor)."),
    )
    can_edit_customers = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Edit existing customers (subject to customer visibility rules for this vendor)."),
    )

    def clean(self):
        super().clean()

        if self.user_id is None or self.vendor_id is None:
            return

        if getattr(self.user, "role", None) != "staff":
            raise ValidationError({"user": _("User must have role='staff'.")})

        qs = Staff.objects.filter(user_id=self.user_id)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                {"user": _("This user is already linked to a staff record.")}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.deleted_at is not None:
            return
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active"])
        User.objects.filter(pk=self.user_id).update(is_active=False)

    def __str__(self) -> str:
        return self.user.get_username()
