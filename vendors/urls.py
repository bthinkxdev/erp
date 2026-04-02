from django.urls import path

from . import views

app_name = "vendors"

urlpatterns = [
    path("settings/", views.vendor_settings, name="settings"),
]
