from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    path(
        "settings/staff-customer-scope/",
        views.toggle_staff_customer_scope,
        name="toggle_staff_customer_scope",
    ),
    path("ledger/dismiss/", views.customer_ledger_dismiss, name="ledger_dismiss"),
    path("", views.customer_list, name="list"),
    path("add/", views.customer_add, name="add"),
    path("<int:pk>/ledger/collect/", views.customer_ledger_collect, name="ledger_collect"),
    path("<int:pk>/ledger/", views.customer_ledger_modal, name="ledger"),
    path("<int:pk>/edit/", views.customer_edit, name="edit"),
    path("<int:pk>/delete/", views.customer_delete, name="delete"),
]
