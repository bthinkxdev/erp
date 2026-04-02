from __future__ import annotations


def is_hx_swap_into(request, element_id: str) -> bool:
    """
    True when this request is HTMX swapping a specific element (e.g. tbody rows).

    Avoid treating every HX-Request as a partial: after a redirect, HTMX replays
    GET with HX-Request set but target is <body>, not the table body.
    """
    if not request.headers.get("HX-Request"):
        return False
    raw = (request.headers.get("HX-Target") or "").strip()
    if raw.startswith("#"):
        raw = raw[1:]
    return raw == element_id
