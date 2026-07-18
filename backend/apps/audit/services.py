from .models import AuditEvent


def record_event(kind, request=None, user=None, description="", success=True, metadata=None):
    return AuditEvent.objects.create(
        event_type=kind,
        user=user if getattr(user, "is_authenticated", False) else None,
        description=description,
        success=success,
        metadata=metadata or {},
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:512] if request else "",
    )
