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
from django.shortcuts import render

from apps.core.models import SystemConfiguration
from apps.licenses.models import License


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
        dumps = list(settings.BACKUP_PATH.glob("licensehub_*.dump"))
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
