import shutil
import ssl
from datetime import datetime, timedelta, timezone

from celery import current_app
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.core.models import SystemConfiguration
from apps.licenses.models import License
from apps.audit.models import AuditEvent
from apps.accounts.models import User
from .forms import (
    BackupSettingsForm,
    LDAPSettingsForm,
    SMTPSettingsForm,
    SystemSettingsForm,
)
from .models import IntegrationSettings
from apps.licenses.crypto import decrypt_secret


def _celery_status():
    try:
        replies = current_app.control.ping(timeout=1.0)
        return "Healthy" if replies else "Critical"
    except Exception:
        return "Critical"


def _beat_status():
    heartbeat = cache.get("celery_beat_heartbeat")
    if heartbeat is None:
        return "Warning"
    age = datetime.now(timezone.utc).timestamp() - float(heartbeat)
    return "Healthy" if age < 150 else "Critical"


def _tls_status():
    cert_path = settings.TLS_MONITOR_CERT_PATH
    if not cert_path.is_file():
        return "Warning"
    try:
        cert = ssl._ssl._test_decode_cert(str(cert_path))
        expires = ssl.cert_time_to_seconds(cert["notAfter"])
        remaining_days = (expires - datetime.now(timezone.utc).timestamp()) / 86400
        if remaining_days <= 0:
            return "Critical"
        return "Warning" if remaining_days < 30 else "Healthy"
    except (OSError, KeyError, ValueError, ssl.SSLError):
        return "Critical"


def checks():
    result = {
        "django": "Healthy",
        "postgresql": "Unknown",
        "redis": "Unknown",
        "celery_worker": "Unknown",
        "celery_beat": "Unknown",
        "disk": "Unknown",
        "backup": "Unknown",
        "tls": "Unknown",
        "static": "Warning",
        "media": "Warning",
    }
    try:
        connection.ensure_connection()
        result["postgresql"] = "Healthy"
    except Exception:
        result["postgresql"] = "Critical"
    try:
        cache.set("health", "ok", 5)
        result["redis"] = "Healthy" if cache.get("health") == "ok" else "Critical"
    except Exception:
        result["redis"] = "Critical"
    result["celery_worker"] = _celery_status()
    result["celery_beat"] = _beat_status()
    try:
        usage = shutil.disk_usage(settings.BASE_DIR)
        result["disk"] = "Warning" if usage.free / usage.total < 0.1 else "Healthy"
    except Exception:
        result["disk"] = "Unknown"
    result["static"] = "Healthy" if settings.STATIC_ROOT.exists() else "Warning"
    result["media"] = "Healthy" if settings.MEDIA_ROOT.exists() else "Warning"
    try:
        dumps = list(settings.BACKUP_PATH.rglob("licensehub_full_*.tar.gz"))
        result["backup"] = "Healthy" if dumps else "Warning"
    except OSError:
        result["backup"] = "Critical"
    result["tls"] = _tls_status()
    return result


def health(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "healthy"})
    except Exception:
        return JsonResponse({"status": "unhealthy"}, status=503)


@login_required
def dashboard(request):
    cfg = SystemConfiguration.objects.first()
    User = get_user_model()
    today = datetime.now(timezone.utc).date()
    active = License.objects.filter(status=License.Status.ACTIVE)
    all_licenses = License.objects.exclude(status=License.Status.ARCHIVED)
    manufacturer_stats = list(
        all_licenses.values("manufacturer__name").annotate(total=Count("id")).order_by("-total")[:5]
    )
    deployment_stats = {
        row["deployment_mode"]: row["total"]
        for row in all_licenses.values("deployment_mode").annotate(total=Count("id"))
    }
    total_licenses = all_licenses.count()
    return render(
        request,
        "dashboard.html",
        {
            "config": cfg,
            "user_count": User.objects.count(),
            "admin_count": User.objects.filter(is_staff=True).count(),
            "license_count": active.count(),
            "total_license_count": total_licenses,
            "manufacturer_stats": manufacturer_stats,
            "deployment_stats": deployment_stats,
            "recent_licenses": all_licenses.select_related("manufacturer").order_by("-created_at")[
                :5
            ],
            "concurrent_count": all_licenses.filter(concurrent=True).count(),
            "expiring_30": active.filter(
                expires_at__gte=today, expires_at__lte=today + timedelta(days=30)
            ).count(),
            "expiring_60": active.filter(
                expires_at__gt=today + timedelta(days=30),
                expires_at__lte=today + timedelta(days=60),
            ).count(),
            "expiring_90": active.filter(
                expires_at__gt=today + timedelta(days=60),
                expires_at__lte=today + timedelta(days=90),
            ).count(),
            "expired_count": License.objects.filter(expires_at__lt=today)
            .exclude(status=License.Status.ARCHIVED)
            .count(),
            "total_cost": active.aggregate(value=Sum("cost"))["value"] or 0,
            "checks": checks(),
        },
    )


@login_required
@user_passes_test(lambda user: user.is_staff)
def system_health(request):
    return render(request, "system/health.html", {"checks": checks()})


@login_required
@user_passes_test(lambda user: user.is_staff)
def audit_log(request):
    events = AuditEvent.objects.select_related("user").all()[:500]
    return render(request, "system/audit.html", {"events": events})


@login_required
@user_passes_test(lambda user: user.is_staff)
def user_list(request):
    return render(
        request, "system/users.html", {"users": User.objects.prefetch_related("groups").all()}
    )


@login_required
@user_passes_test(lambda user: user.is_superuser)
def settings_view(request):
    config = SystemConfiguration.objects.first()
    form = SystemSettingsForm(request.POST or None, instance=config)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("settings")
    return render(request, "system/settings.html", {"form": form})


@login_required
@user_passes_test(lambda user: user.is_superuser)
def ldap_status(request):
    config = IntegrationSettings.get_solo()
    form = LDAPSettingsForm(request.POST or None, instance=config)
    result = None
    if request.method == "POST" and form.is_valid():
        config = form.save()
        result = "Beállítások mentve."
        if "test" in request.POST and config.ldap_enabled:
            try:
                from ldap3 import Connection, Server

                with Connection(
                    Server(config.ldap_server_uri, use_ssl=config.ldap_use_ssl),
                    user=config.ldap_bind_dn,
                    password=decrypt_secret(config.ldap_bind_password),
                    auto_bind=True,
                ):
                    pass
                result = "LDAP kapcsolat sikeres."
            except Exception as exc:
                result = f"LDAP kapcsolat sikertelen: {type(exc).__name__}"
    return render(request, "system/ldap.html", {"form": form, "result": result})


@login_required
@user_passes_test(lambda user: user.is_superuser)
def smtp_test(request):
    config = IntegrationSettings.get_solo()
    form = SMTPSettingsForm(request.POST or None, instance=config)
    result = None
    if request.method == "POST" and form.is_valid():
        config = form.save()
        result = "Beállítások mentve."
        recipient = form.cleaned_data.get("test_recipient")
        if "test" in request.POST and recipient:
            try:
                from django.core.mail import EmailMessage, get_connection

                connection = get_connection(
                    host=config.smtp_host,
                    port=config.smtp_port,
                    username=config.smtp_username,
                    password=decrypt_secret(config.smtp_password),
                    use_tls=config.smtp_use_tls,
                )
                EmailMessage(
                    "LicenseHub SMTP teszt",
                    "A LicenseHub SMTP beállítása működik.",
                    config.smtp_from_email,
                    [recipient],
                    connection=connection,
                ).send()
                result = "Tesztüzenet sikeresen elküldve."
            except Exception as exc:
                result = f"Sikertelen: {type(exc).__name__}"
    return render(request, "system/smtp.html", {"form": form, "result": result})


@login_required
@user_passes_test(lambda user: user.is_superuser)
def backup_dashboard(request):
    config = IntegrationSettings.get_solo()
    form = BackupSettingsForm(request.POST or None, instance=config)
    if request.method == "POST" and "save_settings" in request.POST and form.is_valid():
        form.save()
        return redirect("backup_dashboard")
    if request.method == "POST" and "backup_now" in request.POST:
        settings.BACKUP_PATH.mkdir(parents=True, exist_ok=True)
        (settings.BACKUP_PATH / ".backup-request").touch()
        return redirect("backup_dashboard")
    files = (
        sorted(
            settings.BACKUP_PATH.rglob("licensehub_full_*.tar.gz"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if settings.BACKUP_PATH.exists()
        else []
    )
    return render(
        request,
        "system/backup.html",
        {"backups": files[:100], "form": form, "config": config},
    )
