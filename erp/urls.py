from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import include, path
import os


def home_redirect(request):
    return redirect("reports:dashboard")


urlpatterns = [
    path("admin/",       admin.site.urls),
    path("",             home_redirect,                       name="home"),
    path("store/",       include("products.store_urls", namespace="store")),
    path("accounts/",    include("accounts.urls")),
    path("reports/",     include("reports.urls")),
    path("customers/",   include("customers.urls")),
    path("collections/", include("erp_collections.urls")),
    path("products/",    include("products.urls")),
    path("staff/",       include("staff.urls")),
    path("vendor/",     include("vendors.urls")),
]

if settings.DEBUG or os.getenv("DJANGO_SERVE_MEDIA", "").lower() in ("1", "true", "yes"):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
