from __future__ import annotations

from utils.vendor import get_vendor_from_request


class VendorMiddleware:
    """
    Attach resolved vendor context to request as `request.vendor`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.vendor = None
        try:
            request.vendor = get_vendor_from_request(request)
        except Exception:
            # Fail closed: keep request.vendor as None
            request.vendor = None
        return self.get_response(request)

