from django.urls import path

from . import views

app_name = "staff"

urlpatterns = [
    path("", views.staff_list, name="list"),
    path("add/", views.staff_add, name="add"),
    path(
        "collections-ledger/modal/",
        views.vendor_collections_ledger_modal,
        name="collections_ledger_modal",
    ),
    path(
        "collections-ledger/dismiss/",
        views.vendor_collections_ledger_dismiss,
        name="collections_ledger_dismiss",
    ),
    path("<int:pk>/edit/", views.staff_edit, name="edit"),
    path("<int:pk>/delete/", views.staff_delete, name="delete"),
]
