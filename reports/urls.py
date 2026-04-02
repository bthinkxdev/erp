from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("analytics/", views.analytics_view, name="analytics"),
    path("htmx/today/", views.today_collection_htmx, name="htmx-today"),
    path("htmx/week/", views.weekly_collection_htmx, name="htmx-week"),
    path("htmx/staff/", views.staff_report_htmx, name="htmx-staff"),
    path("htmx/date-range/", views.date_range_report_htmx, name="htmx-date-range"),
    path("htmx/staff-analytics/", views.staff_analytics_htmx, name="htmx-staff-analytics"),
    path(
        "htmx/customer-analytics/",
        views.customer_analytics_htmx,
        name="htmx-customer-analytics",
    ),
    path("export/csv/", views.export_csv_view, name="export-csv"),
]

