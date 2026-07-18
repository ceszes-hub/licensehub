from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class SystemConfiguration(models.Model):
    singleton = models.BooleanField(default=True, unique=True, editable=False)
    company_name = models.CharField(max_length=200)
    company_short_name = models.CharField(max_length=50)
    country = models.CharField(max_length=2, default="HU")
    timezone = models.CharField(max_length=64, default="Europe/Budapest")
    language = models.CharField(max_length=10, default="hu")
    support_email = models.EmailField()
    support_phone = models.CharField(max_length=40, blank=True)
    setup_completed = models.BooleanField(default=False)
    installation_date = models.DateTimeField(null=True, blank=True)
    application_version = models.CharField(max_length=30, default="1.0-dev0")
    first_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if SystemConfiguration.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Only one system configuration is allowed.")

    def save(self, *a, **kw):
        self.full_clean()
        return super().save(*a, **kw)
