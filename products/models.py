from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from vendors.models import VendorAwareModel


class ProductCategory(VendorAwareModel):
    name = models.CharField(max_length=255, db_index=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("vendor", "name"),
                condition=models.Q(deleted_at__isnull=True),
                name="uniq_productcategory_vendor_name_active",
            )
        ]
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Product(VendorAwareModel):
    category = models.ForeignKey(
        "products.ProductCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        db_index=True,
    )
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=("vendor", "name"), name="idx_product_vendor_name"),
            models.Index(fields=("vendor", "is_active"), name="idx_product_vendor_active"),
            models.Index(fields=("vendor", "category"), name="idx_product_vendor_category"),
        ]
        ordering = ("-created_at",)

    def clean(self):
        super().clean()
        if self.price is None or self.mrp is None:
            return
        if self.price > self.mrp:
            raise ValidationError({"price": _("Price must be less than or equal to MRP.")})
        if self.category_id and self.vendor_id:
            if getattr(self.category, "vendor_id", None) != self.vendor_id:
                raise ValidationError({"category": _("Category must belong to this vendor.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        vendor_name = getattr(self.vendor, "name", self.vendor_id)
        return f"{self.name} - {vendor_name}"
