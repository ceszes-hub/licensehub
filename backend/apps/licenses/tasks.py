from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from celery import shared_task
from .models import License, NotificationLog


@shared_task
def send_expiry_notifications():
    today = timezone.localdate()
    sent = 0
    for license_obj in License.objects.filter(
        status__in=[License.Status.ACTIVE, License.Status.EXPIRING], expires_at__isnull=False
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
        body = f"A(z) {license_obj.name} licenc {days} napon belül lejár.\nLejárat: {license_obj.expires_at}\nDarabszám: {license_obj.quantity}\nGyártó: {license_obj.manufacturer or '-'}\nDisztribútor: {license_obj.distributor or '-'}\nFelelős: {license_obj.owner or '-'}"
        log = NotificationLog.objects.create(
            license=license_obj, interval_days=days, recipients=sorted(recipients)
        )
        try:
            send_mail(
                subject, body, settings.DEFAULT_FROM_EMAIL, sorted(recipients), fail_silently=False
            )
            log.success = True
            sent += 1
        except Exception as exc:
            log.error = str(exc)[:1000]
        log.save(update_fields=["success", "error"])
    return {"sent": sent}
