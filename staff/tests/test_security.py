from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from customers.models import Customer
from erp_collections.models import Collection
from staff.models import Staff
from users.models import User
from utils.queryset import secure_queryset
from utils.security import (
    collection_mutation_allowed,
    staff_category_mutation_allowed,
    staff_customer_add_allowed,
    staff_customer_edit_allowed,
    staff_export_allowed,
    staff_product_mutation_allowed,
)
from vendors.models import Vendor

UserModel = get_user_model()


def _rf(user, vendor=None):
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    request.vendor = vendor
    return request


class SecureQuerysetTests(TestCase):
    def setUp(self):
        self.vendor_a = Vendor.objects.create(
            name="Vendor A",
            whatsapp_number="919999900010",
            owner=UserModel.objects.create_user(
                "va", "va@example.com", "pass", role=User.Roles.VENDOR
            ),
        )
        self.vendor_b = Vendor.objects.create(
            name="Vendor B",
            whatsapp_number="919999900020",
            owner=UserModel.objects.create_user(
                "vb", "vb@example.com", "pass", role=User.Roles.VENDOR
            ),
        )
        self.staff_a1 = UserModel.objects.create_user(
            "a1", "a1@example.com", "pass", role=User.Roles.STAFF
        )
        self.staff_row_a1 = Staff.objects.create(
            user=self.staff_a1,
            vendor=self.vendor_a,
            whatsapp_number="919999900111",
        )
        self.staff_a2 = UserModel.objects.create_user(
            "a2", "a2@example.com", "pass", role=User.Roles.STAFF
        )
        self.staff_row_a2 = Staff.objects.create(
            user=self.staff_a2,
            vendor=self.vendor_a,
            whatsapp_number="919999900112",
        )
        self.cust = Customer.objects.create(
            vendor=self.vendor_a, name="C", phone="1", address=""
        )
        self.col_a1 = Collection.objects.create(
            vendor=self.vendor_a,
            staff=self.staff_row_a1,
            customer=self.cust,
            amount=Decimal("10"),
            day_number=1,
            week_number=1,
        )
        self.col_a2 = Collection.objects.create(
            vendor=self.vendor_a,
            staff=self.staff_row_a2,
            customer=self.cust,
            amount=Decimal("20"),
            day_number=1,
            week_number=1,
        )

    def test_staff_sees_only_own_collections_without_flag(self):
        req = _rf(self.staff_a1, self.vendor_a)
        qs = secure_queryset(Collection.objects.all(), req)
        self.assertEqual(set(qs.values_list("pk", flat=True)), {self.col_a1.pk})

    def test_staff_sees_all_collections_with_flag(self):
        self.staff_row_a1.can_view_all_collections = True
        self.staff_row_a1.save(update_fields=["can_view_all_collections"])
        req = _rf(self.staff_a1, self.vendor_a)
        qs = secure_queryset(Collection.objects.all(), req)
        self.assertEqual(
            set(qs.values_list("pk", flat=True)), {self.col_a1.pk, self.col_a2.pk}
        )

    def test_staff_profile_is_self_only(self):
        req = _rf(self.staff_a1, self.vendor_a)
        qs = secure_queryset(Staff.objects.all(), req)
        self.assertEqual(list(qs), [self.staff_row_a1])

    def test_vendor_sees_vendor_collections(self):
        req = _rf(self.vendor_a.owner, self.vendor_a)
        qs = secure_queryset(Collection.objects.all(), req)
        self.assertEqual(
            set(qs.values_list("pk", flat=True)), {self.col_a1.pk, self.col_a2.pk}
        )

    def test_no_cross_vendor(self):
        req = _rf(self.staff_a1, self.vendor_a)
        qs = secure_queryset(Collection.objects.all(), req)
        self.assertEqual(qs.filter(vendor=self.vendor_b).count(), 0)

    def test_superuser_sees_all_without_vendor_context(self):
        """createsuperuser defaults role=staff; admin must still list tenant data."""
        su = UserModel.objects.create_user(
            "superu",
            "superu@example.com",
            "pass",
            role=User.Roles.STAFF,
            is_staff=True,
            is_superuser=True,
        )
        req = _rf(su, vendor=None)
        qs_staff = secure_queryset(Staff.objects.all(), req)
        qs_vendor = secure_queryset(Vendor.objects.all(), req)
        self.assertGreaterEqual(qs_staff.count(), 2)
        self.assertGreaterEqual(qs_vendor.count(), 2)

    def test_erp_admin_role_sees_all(self):
        admin_u = UserModel.objects.create_user(
            "adm", "adm@example.com", "pass", role=User.Roles.ADMIN
        )
        req = _rf(admin_u, vendor=None)
        self.assertGreaterEqual(secure_queryset(Vendor.objects.all(), req).count(), 2)


class CollectionMutationTests(TestCase):
    def setUp(self):
        self.vendor = Vendor.objects.create(
            name="V",
            whatsapp_number="919999900030",
            owner=UserModel.objects.create_user("vo", "vo@e.com", "p", role=User.Roles.VENDOR),
        )
        self.su = UserModel.objects.create_user("su", "su@e.com", "p", role=User.Roles.STAFF)
        self.srow = Staff.objects.create(
            user=self.su, vendor=self.vendor, whatsapp_number="919999900121"
        )
        self.other_u = UserModel.objects.create_user("ou", "ou@e.com", "p", role=User.Roles.STAFF)
        self.other_row = Staff.objects.create(
            user=self.other_u, vendor=self.vendor, whatsapp_number="919999900122"
        )
        self.cust = Customer.objects.create(vendor=self.vendor, name="N", phone="9", address="")
        self.own_col = Collection.objects.create(
            vendor=self.vendor,
            staff=self.srow,
            customer=self.cust,
            amount=Decimal("1"),
            day_number=1,
            week_number=1,
        )
        self.other_col = Collection.objects.create(
            vendor=self.vendor,
            staff=self.other_row,
            customer=self.cust,
            amount=Decimal("2"),
            day_number=1,
            week_number=1,
        )

    def test_staff_edits_own_always(self):
        req = _rf(self.su, self.vendor)
        self.assertTrue(collection_mutation_allowed(req, self.own_col))

    def test_staff_cannot_edit_other_without_flag(self):
        req = _rf(self.su, self.vendor)
        self.assertFalse(collection_mutation_allowed(req, self.other_col))

    def test_staff_edits_other_with_flag(self):
        self.srow.can_edit_collection = True
        self.srow.save(update_fields=["can_edit_collection"])
        req = _rf(self.su, self.vendor)
        self.assertTrue(collection_mutation_allowed(req, self.other_col))


class ExportPermissionTests(TestCase):
    def test_staff_export_requires_flag(self):
        vendor = Vendor.objects.create(
            name="V2",
            whatsapp_number="919999900040",
            owner=UserModel.objects.create_user("v2", "v2@e.com", "p", role=User.Roles.VENDOR),
        )
        u = UserModel.objects.create_user("st", "st@e.com", "p", role=User.Roles.STAFF)
        Staff.objects.create(
            user=u,
            vendor=vendor,
            whatsapp_number="919999900131",
            can_export_data=False,
        )
        req = _rf(u, vendor)
        self.assertFalse(staff_export_allowed(req))

        Staff.objects.filter(user=u).update(can_export_data=True)
        self.assertTrue(staff_export_allowed(req))

    def test_vendor_export_allowed(self):
        vendor = Vendor.objects.create(
            name="V3",
            whatsapp_number="919999900050",
            owner=UserModel.objects.create_user("v3", "v3@e.com", "p", role=User.Roles.VENDOR),
        )
        req = _rf(vendor.owner, vendor)
        self.assertTrue(staff_export_allowed(req))


class ProductCategoryStaffPermissionTests(TestCase):
    def setUp(self):
        self.vendor = Vendor.objects.create(
            name="PV",
            whatsapp_number="919999900060",
            owner=UserModel.objects.create_user("pvo", "pvo@e.com", "p", role=User.Roles.VENDOR),
        )
        self.staff_u = UserModel.objects.create_user("pst", "pst@e.com", "p", role=User.Roles.STAFF)
        self.staff_row = Staff.objects.create(
            user=self.staff_u,
            vendor=self.vendor,
            whatsapp_number="919999900141",
            can_manage_products=False,
            can_manage_categories=False,
        )

    def test_vendor_product_and_category_allowed(self):
        req = _rf(self.vendor.owner, self.vendor)
        self.assertTrue(staff_product_mutation_allowed(req))
        self.assertTrue(staff_category_mutation_allowed(req))

    def test_staff_product_requires_flag(self):
        req = _rf(self.staff_u, self.vendor)
        self.assertFalse(staff_product_mutation_allowed(req))
        Staff.objects.filter(pk=self.staff_row.pk).update(can_manage_products=True)
        self.staff_row.refresh_from_db()
        self.assertTrue(staff_product_mutation_allowed(req))

    def test_staff_category_requires_flag(self):
        req = _rf(self.staff_u, self.vendor)
        self.assertFalse(staff_category_mutation_allowed(req))
        Staff.objects.filter(pk=self.staff_row.pk).update(can_manage_categories=True)
        self.staff_row.refresh_from_db()
        self.assertTrue(staff_category_mutation_allowed(req))


class CustomerStaffPermissionTests(TestCase):
    def setUp(self):
        self.vendor = Vendor.objects.create(
            name="CV",
            whatsapp_number="919999900070",
            owner=UserModel.objects.create_user("cvo", "cvo@e.com", "p", role=User.Roles.VENDOR),
        )
        self.staff_u = UserModel.objects.create_user("cst", "cst@e.com", "p", role=User.Roles.STAFF)
        self.staff_row = Staff.objects.create(
            user=self.staff_u,
            vendor=self.vendor,
            whatsapp_number="919999900151",
            can_add_customers=False,
            can_edit_customers=False,
        )

    def test_vendor_customer_add_and_edit_allowed(self):
        req = _rf(self.vendor.owner, self.vendor)
        self.assertTrue(staff_customer_add_allowed(req))
        self.assertTrue(staff_customer_edit_allowed(req))

    def test_staff_add_requires_can_add_customers(self):
        req = _rf(self.staff_u, self.vendor)
        self.assertFalse(staff_customer_add_allowed(req))
        Staff.objects.filter(pk=self.staff_row.pk).update(can_add_customers=True)
        self.staff_row.refresh_from_db()
        self.assertTrue(staff_customer_add_allowed(req))
        self.assertFalse(staff_customer_edit_allowed(req))

    def test_staff_edit_requires_can_edit_customers(self):
        req = _rf(self.staff_u, self.vendor)
        self.assertFalse(staff_customer_edit_allowed(req))
        Staff.objects.filter(pk=self.staff_row.pk).update(can_edit_customers=True)
        self.staff_row.refresh_from_db()
        self.assertTrue(staff_customer_edit_allowed(req))
        self.assertFalse(staff_customer_add_allowed(req))
