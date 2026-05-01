from django.test import SimpleTestCase

from products.forms import ProductForm
from utils.whatsapp import build_whatsapp_order_message


class OptionalProductPriceTests(SimpleTestCase):
    def test_product_form_allows_blank_price(self):
        form = ProductForm(
            data={
                "name": "Sample Product",
                "category": "",
                "description": "",
                "price": "",
                "mrp": "",
                "is_active": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["price"])

    def test_whatsapp_message_omits_blank_price(self):
        message = build_whatsapp_order_message(
            product_name="Sample Product",
            price=None,
        )

        self.assertIn("Product: Sample Product", message)
        self.assertNotIn("Price:", message)
