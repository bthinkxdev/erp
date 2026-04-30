from django.urls import path

from . import store_views

app_name = "store"

urlpatterns = [
    path("<int:vendor_id>/", store_views.store_home, name="home"),
    path(
        "<int:vendor_id>/category/<int:category_id>/",
        store_views.store_category_products,
        name="category",
    ),
    path(
        "<int:vendor_id>/product/<int:product_id>/",
        store_views.store_product_detail,
        name="product_detail",
    ),
]
