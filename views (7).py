"""App configuration for amendments app."""
from django.apps import AppConfig


class AmendmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.amendments"
    verbose_name = "Contract Amendments"
