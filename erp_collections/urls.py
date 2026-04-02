from django.urls import path

from . import views

app_name = "collections"

urlpatterns = [
    path("", views.day_dashboard, name="list"),
    path("history/", views.collection_list, name="history"),
    path("add/", views.collection_add, name="add"),
    path("<int:pk>/edit/", views.collection_edit, name="edit"),
    path("day/<int:day>/customers/", views.get_customers_by_day_htmx, name="customers_by_day"),
]
