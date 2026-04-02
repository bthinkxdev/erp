from django.apps import AppConfig


class CollectionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Module path is `erp_collections` (we avoid clashing with stdlib `collections`).
    name = "erp_collections"
    # Logical app label is kept as `collections` for consistency with your domain naming.
    label = "collections"

