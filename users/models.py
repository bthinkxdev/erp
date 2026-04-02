from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    """
    Shared base fields for all future database models.
    """

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractUser, BaseModel):
    class Roles(models.TextChoices):
        ADMIN = "admin", _("Admin")
        VENDOR = "vendor", _("Vendor")
        STAFF = "staff", _("Staff")

    # Keep `username` from AbstractUser for now (do not remove).
    role = models.CharField(max_length=16, choices=Roles.choices, default=Roles.STAFF)

    # Unique email is foundation-ready for future "login via email" flows.
    email = models.EmailField(_("email address"), unique=True)

    # Ensure Django still authenticates with username until we intentionally switch.
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]
    EMAIL_FIELD = "email"

    @property
    def is_admin(self) -> bool:
        return self.role == self.Roles.ADMIN

    @property
    def is_vendor(self) -> bool:
        return self.role == self.Roles.VENDOR

    @property
    def is_staff_user(self) -> bool:
        return self.role == self.Roles.STAFF

    @property
    def vendor_profile(self):
        return getattr(self, "vendor", None)

    @property
    def staff_profile(self):
        staff_model = type(self)._meta.apps.get_model("staff", "Staff")
        try:
            return staff_model.objects.select_related("vendor").get(user_id=self.pk)
        except staff_model.DoesNotExist:
            return None

    @property
    def reports_allowed(self) -> bool:
        if self.is_admin or self.is_vendor:
            return True
        sp = self.staff_profile
        return sp is not None and sp.can_view_reports

    @property
    def export_allowed(self) -> bool:
        if self.is_admin or self.is_vendor:
            return True
        sp = self.staff_profile
        return sp is not None and sp.can_export_data

    def can_edit_collection_object(self, collection) -> bool:
        if self.is_admin or self.is_vendor:
            return True
        sp = self.staff_profile
        if sp is None:
            return False
        if collection.staff_id == sp.pk:
            return True
        return bool(sp.can_edit_collection)

    @property
    def can_manage_products(self) -> bool:
        if self.is_admin or self.is_vendor:
            return True
        sp = self.staff_profile
        return sp is not None and sp.can_manage_products

    @property
    def can_manage_categories(self) -> bool:
        if self.is_admin or self.is_vendor:
            return True
        sp = self.staff_profile
        return sp is not None and sp.can_manage_categories

    @property
    def can_add_customers(self) -> bool:
        if self.is_admin or self.is_vendor:
            return True
        sp = self.staff_profile
        return sp is not None and sp.can_add_customers

    @property
    def can_edit_customers(self) -> bool:
        if self.is_admin or self.is_vendor:
            return True
        sp = self.staff_profile
        return sp is not None and sp.can_edit_customers

    def __str__(self) -> str:
        return self.get_username()

