from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.utils import timezone

from apps.system.models import IntegrationSettings

from .crypto import decrypt_secret
from .models import License, NotificationLog


def _email_connection():
    config = IntegrationSettings.objects.first()
    if config is None or not config.smtp_host:
        return get_connection(), settings.DEFAULT_FROM_EMAIL
    connection = get_connection(
        host=config.smtp_host,
        port=config.smtp_port,
        username=config.smtp_username,
        password=decrypt_secret(config.smtp_password),
        use_tls=config.smtp_use_tls,
    )
    return connection, config.smtp_from_email or settings.DEFAULT_FROM_EMAIL


@shared_task
def send_expiry_notifications():
    today = timezone.localdate()
    sent = 0
    connection, from_email = _email_connection()
    for license_obj in License.objects.filter(
        status__in=[License.Status.ACTIVE, License.Status.EXPIRING],
        expires_at__isnull=False,
    ):
        days = (license_obj.expires_at - today).days
        if (
            days not in license_obj.notification_intervals
            or NotificationLog.objects.filter(license=license_obj, interval_days=days).exists()
        ):
            continue
        recipients = set(license_obj.notification_emails)
        recipients.update(
            license_obj.notification_users.exclude(email="").values_list("email", flat=True)
        )
        if not recipients:
            continue
        subject = f"Licenc hamarosan lejár – {license_obj.name}"
        body = (
            f"A(z) {license_obj.name} licenc {days} napon belül lejár.\n"
            f"Lejárat: {license_obj.expires_at}\n"
            f"Darabszám: {license_obj.quantity}\n"
            f"Gyártó: {license_obj.manufacturer or '-'}\n"
            f"Disztribútor: {license_obj.distributor or '-'}\n"
            f"Felelős: {license_obj.owner or '-'}"
        )
        log = NotificationLog.objects.create(
            license=license_obj,
            interval_days=days,
            recipients=sorted(recipients),
        )
        try:
            EmailMessage(
                subject,
                body,
                from_email,
                sorted(recipients),
                connection=connection,
            ).send(fail_silently=False)
            log.success = True
            sent += 1
        except Exception as exc:
            log.error = str(exc)[:1000]
        log.save(update_fields=["success", "error"])
    return {"sent": sent}
