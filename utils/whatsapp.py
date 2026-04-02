from __future__ import annotations

import re
from decimal import Decimal
from urllib.parse import quote

from staff.models import Staff
from vendors.models import Vendor


def normalize_wa_me_number(raw: str) -> str:
    """Digits only for https://wa.me/<number>."""
    if not raw:
        return ""
    return re.sub(r"\D", "", str(raw))


def build_whatsapp_order_message(*, product_name: str, price) -> str:
    if isinstance(price, Decimal):
        price_str = f"{price:.2f}"
    else:
        price_str = str(price)
    return (
        "Hello, I want to order:\n\n"
        f"Product: {product_name}\n"
        f"Price: {price_str}"
    )


def whatsapp_order_url_for_product(
    vendor: Vendor,
    staff: Staff | None,
    *,
    product_name: str,
    price,
) -> str | None:
    """
    Build https://wa.me/<number>?text=... using staff WhatsApp when scoped to a
    staff link, otherwise the vendor business number.
    """
    raw_phone = staff.whatsapp_number if staff is not None else vendor.whatsapp_number
    phone = normalize_wa_me_number(raw_phone or "")
    if not phone:
        return None
    text = build_whatsapp_order_message(product_name=product_name, price=price)
    return f"https://wa.me/{phone}?text={quote(text)}"


_GENERAL_CHAT_MESSAGE = (
    "Hello! I'd like to place an order from your store. Could you help me?"
)


def whatsapp_general_order_url(vendor: Vendor, staff: Staff | None) -> str | None:
    """Open WhatsApp with a generic order intent (e.g. sticky bar)."""
    raw_phone = staff.whatsapp_number if staff is not None else vendor.whatsapp_number
    phone = normalize_wa_me_number(raw_phone or "")
    if not phone:
        return None
    return f"https://wa.me/{phone}?text={quote(_GENERAL_CHAT_MESSAGE)}"
