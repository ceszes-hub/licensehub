from django.db import models


class IntegrationSettings(models.Model):
    class BackupDestination(models.TextChoices):
        LOCAL = "LOCAL", "Helyi tárhely"
        S3 = "S3", "Amazon S3"
        AZURE = "AZURE", "Azure Blob Storage"
        SHAREPOINT = "SHAREPOINT", "Microsoft SharePoint"
        SMB = "SMB", "SMB hálózati megosztás"

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
    backup_retention_days = models.PositiveIntegerField(default=14)
    backup_interval_hours = models.PositiveIntegerField(default=24)
    backup_destination = models.CharField(
        max_length=20, choices=BackupDestination.choices, default=BackupDestination.LOCAL
    )
    backup_local_subdirectory = models.CharField(max_length=100, default="full")
    backup_remote_path = models.CharField(max_length=500, blank=True)
    backup_smb_host = models.CharField(max_length=255, blank=True)
    backup_smb_share = models.CharField(max_length=255, blank=True)
    backup_smb_subdirectory = models.CharField(max_length=255, blank=True)
    backup_smb_domain = models.CharField(max_length=100, blank=True)
    backup_smb_username = models.CharField(max_length=255, blank=True)
    backup_smb_password = models.TextField(blank=True)
    backup_smb_port = models.PositiveIntegerField(default=445)
    network_hostname = models.CharField(max_length=63, blank=True)
    network_interface = models.CharField(max_length=50, default="ens18")
    network_dhcp = models.BooleanField(default=True)
    network_address = models.CharField(max_length=64, blank=True)
    network_gateway = models.GenericIPAddressField(null=True, blank=True)
    network_dns_primary = models.GenericIPAddressField(null=True, blank=True)
    network_dns_secondary = models.GenericIPAddressField(null=True, blank=True)
    network_search_domain = models.CharField(max_length=255, blank=True)
    network_public_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        return cls.objects.get_or_create(singleton=True)[0]
