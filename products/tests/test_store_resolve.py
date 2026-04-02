from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from products.models import Product, ProductCategory
from staff.models import Staff
from users.models import User
from vendors.models import Vendor

UserModel = get_user_model()


class StoreStaffSessionTests(TestCase):
    def setUp(self):
        self.vendor = Vendor.objects.create(
            name="V",
            whatsapp_number="919999900001",
            owner=UserModel.objects.create_user(
                "vo", "vo@e.com", "p", role=User.Roles.VENDOR
            ),
        )
        self.staff_user = UserModel.objects.create_user(
            "su", "su@e.com", "p", role=User.Roles.STAFF
        )
        self.staff = Staff.objects.create(
            user=self.staff_user,
            vendor=self.vendor,
            whatsapp_number="919999900002",
        )
        self.cat = ProductCategory.objects.create(
            vendor=self.vendor, name="C1", is_active=True
        )
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.cat,
            name="P1",
            mrp=Decimal("100"),
            price=Decimal("80"),
            is_active=True,
        )
        self.client = Client()

    def test_category_without_query_keeps_staff_after_staff_home_visit(self):
        url_home_staff = reverse(
            "store:home", kwargs={"vendor_id": self.vendor.pk}
        ) + f"?staff={self.staff.pk}"
        self.client.get(url_home_staff)
        url_cat = reverse(
            "store:category",
            kwargs={"vendor_id": self.vendor.pk, "category_id": self.cat.pk},
        )
        r = self.client.get(url_cat)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["store_staff"].pk, self.staff.pk)

    def test_store_home_without_query_clears_staff_scope(self):
        self.client.get(
            reverse("store:home", kwargs={"vendor_id": self.vendor.pk})
            + f"?staff={self.staff.pk}"
        )
        r = self.client.get(
            reverse("store:home", kwargs={"vendor_id": self.vendor.pk})
        )
        self.assertIsNone(r.context["store_staff"])

    def test_category_without_session_has_no_staff(self):
        url_cat = reverse(
            "store:category",
            kwargs={"vendor_id": self.vendor.pk, "category_id": self.cat.pk},
        )
        r = self.client.get(url_cat)
        self.assertIsNone(r.context["store_staff"])
