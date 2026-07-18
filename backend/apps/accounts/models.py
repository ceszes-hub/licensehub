from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class AccountType(models.TextChoices):
        LOCAL = "LOCAL", "Local"
        LDAP = "LDAP", "LDAP"
        SERVICE = "SERVICE", "Service"

    account_type = models.CharField(
        max_length=10, choices=AccountType.choices, default=AccountType.LOCAL
    )
    force_password_change = models.BooleanField(default=False)
    mfa_required = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
