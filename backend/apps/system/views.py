import shutil
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from apps.core.models import SystemConfiguration


def checks():
    result = {
        "django": "Healthy",
        "postgresql": "Unknown",
        "redis": "Unknown",
        "celery": "Unknown",
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
    try:
        u = shutil.disk_usage(settings.BASE_DIR)
        result["disk"] = "Warning" if u.free / u.total < 0.1 else "Healthy"
    except Exception:
        result["disk"] = "Unknown"
    result["static"] = "Healthy" if settings.STATIC_ROOT.exists() else "Warning"
    result["media"] = "Healthy" if settings.MEDIA_ROOT.exists() else "Warning"
    result["backup"] = "Healthy" if settings.BACKUP_PATH.exists() else "Warning"
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
    return render(
        request,
        "dashboard.html",
        {
            "config": cfg,
            "user_count": User.objects.count(),
            "admin_count": User.objects.filter(is_staff=True).count(),
            "checks": checks(),
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def system_health(request):
    return render(request, "system/health.html", {"checks": checks()})
