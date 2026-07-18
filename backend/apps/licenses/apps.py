from django.apps import AppConfig


class LicensesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.licenses"
    label = "licenses"

    def ready(self):
        from django.db.models.signals import post_migrate
        from .roles import ensure_license_roles

        post_migrate.connect(ensure_license_roles, sender=self)
