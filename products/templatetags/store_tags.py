from __future__ import annotations

from decimal import Decimal

from django import template

from utils.whatsapp import (
    whatsapp_general_order_url,
    whatsapp_order_url_for_product,
)

register = template.Library()


@register.simple_tag
def whatsapp_order_url(store_vendor, store_staff, product):
    if product is None:
        return None
    return whatsapp_order_url_for_product(
        store_vendor,
        store_staff,
        product_name=product.name,
        price=product.price,
    )


@register.simple_tag
def whatsapp_chat_order_url(store_vendor, store_staff):
    return whatsapp_general_order_url(store_vendor, store_staff)


def _discount_pct_for_product(product):
    if product is None:
        return None
    mrp = getattr(product, "mrp", None)
    price = getattr(product, "price", None)
    if mrp is None or price is None:
        return None
    try:
        m = Decimal(str(mrp))
        p = Decimal(str(price))
    except Exception:
        return None
    if m <= 0 or m <= p:
        return None
    return int(round((1 - p / m) * 100))


@register.simple_tag
def discount_pct_for(product):
    """Integer percent off when MRP > price; use {% discount_pct_for product as pct_off %}."""
    return _discount_pct_for_product(product)


@register.filter
def discount_pct(product):
    """Use in pipes: {{ product|discount_pct }}."""
    return _discount_pct_for_product(product)
