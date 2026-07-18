from django.db import models


class IntegrationSettings(models.Model):
    singleton = models.BooleanField(default=True, unique=True, editable=False)
    ldap_enabled = models.BooleanField(default=False)
    ldap_server_uri = models.CharField(max_length=255, blank=True)
    ldap_use_ssl = models.BooleanField(default=True)
    ldap_base_dn = models.CharField(max_length=255, blank=True)
    ldap_bind_dn = models.CharField(max_length=255, blank=True)
    ldap_bind_password = models.TextField(blank=True)
    ldap_user_filter = models.CharField(max_length=255, default="(sAMAccountName={username})")
    ldap_admin_group = models.CharField(max_length=255, blank=True)
    ldap_manager_group = models.CharField(max_length=255, blank=True)
    ldap_reader_group = models.CharField(max_length=255, blank=True)
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_use_tls = models.BooleanField(default=True)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.TextField(blank=True)
    smtp_from_email = models.EmailField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        return cls.objects.get_or_create(singleton=True)[0]
