from django.urls import path

from . import views
from . import views_category

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("add/", views.product_add, name="add"),
    path("<int:pk>/edit/", views.product_edit, name="edit"),
    path("<int:pk>/delete/", views.product_delete, name="delete"),
    path("categories/", views_category.category_modal, name="category_modal"),
    path("categories/dismiss/", views_category.category_dismiss, name="category_dismiss"),
    path("categories/panel/", views_category.category_panel, name="category_panel"),
    path("categories/add/", views_category.category_add, name="category_add"),
    path("categories/<int:pk>/edit/", views_category.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views_category.category_delete, name="category_delete"),
]
