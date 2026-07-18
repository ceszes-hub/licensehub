from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Party(models.Model):
    class Kind(models.TextChoices):
        MANUFACTURER = "MANUFACTURER", "Gyártó"
        DISTRIBUTOR = "DISTRIBUTOR", "Disztribútor"

    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    active = models.BooleanField(default=True)
    postal_code = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["name", "kind"], name="unique_party_kind")]

    def __str__(self):
        return self.name


class PartyContact(models.Model):
    party = models.ForeignKey(Party, related_name="contacts", on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    position = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.party.name})"


class License(models.Model):
    class Deployment(models.TextChoices):
        CLOUD = "CLOUD", "Felhő"
        ON_PREMISES = "ON_PREMISES", "On-premises"
        HYBRID = "HYBRID", "Hibrid"

    class LicenseType(models.TextChoices):
        SUBSCRIPTION = "SUBSCRIPTION", "Előfizetés"
        PERPETUAL = "PERPETUAL", "Örökös"
        TRIAL = "TRIAL", "Próba"
        OTHER = "OTHER", "Egyéb"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Aktív"
        EXPIRING = "EXPIRING", "Lejáró"
        EXPIRED = "EXPIRED", "Lejárt"
        TERMINATED = "TERMINATED", "Megszüntetett"
        ARCHIVED = "ARCHIVED", "Archivált"

    name = models.CharField(max_length=255)
    manufacturer = models.ForeignKey(
        Party,
        null=True,
        blank=True,
        related_name="manufactured_licenses",
        on_delete=models.PROTECT,
        limit_choices_to={"kind": Party.Kind.MANUFACTURER},
    )
    distributor = models.ForeignKey(
        Party,
        null=True,
        blank=True,
        related_name="distributed_licenses",
        on_delete=models.PROTECT,
        limit_choices_to={"kind": Party.Kind.DISTRIBUTOR},
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    deployment_mode = models.CharField(max_length=20, choices=Deployment.choices)
    concurrent = models.BooleanField(default=False)
    concurrent_limit = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    license_type = models.CharField(max_length=20, choices=LicenseType.choices)
    secret_reference = models.TextField(blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True, db_index=True)
    auto_renews = models.BooleanField(default=False)
    notification_intervals = models.JSONField(default=list, blank=True)
    notification_emails = models.JSONField(default=list, blank=True)
    notification_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="license_notifications"
    )
    cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="HUF")
    cost_center = models.CharField(max_length=100, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="owned_licenses",
        on_delete=models.SET_NULL,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        related_name="licenses_created",
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        related_name="licenses_updated",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        permissions = [
            ("export_license", "Can export licenses"),
            ("archive_license", "Can archive licenses"),
        ]

    def clean(self):
        if self.concurrent and not self.concurrent_limit:
            raise ValidationError({"concurrent_limit": "Konkurens licencnél a limit kötelező."})
        if not self.concurrent:
            self.concurrent_limit = None
        if self.valid_from and self.expires_at and self.expires_at < self.valid_from:
            raise ValidationError({"expires_at": "A lejárat nem előzheti meg a kezdő dátumot."})

    @property
    def days_until_expiry(self):
        return (self.expires_at - timezone.localdate()).days if self.expires_at else None

    def __str__(self):
        return self.name


class LicenseDocument(models.Model):
    license = models.ForeignKey(License, related_name="documents", on_delete=models.CASCADE)
    file = models.FileField(upload_to="licenses/%Y/%m/")
    original_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class NotificationLog(models.Model):
    license = models.ForeignKey(License, related_name="notification_logs", on_delete=models.CASCADE)
    interval_days = models.PositiveIntegerField()
    recipients = models.JSONField(default=list)
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    error = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["license", "interval_days"], name="unique_license_interval_notification"
            )
        ]
