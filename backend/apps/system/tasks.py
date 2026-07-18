from datetime import datetime, timezone
from celery import shared_task
from django.core.cache import cache


@shared_task
def periodic_health_check():
    timestamp = datetime.now(timezone.utc).timestamp()
    cache.set("celery_beat_heartbeat", timestamp, timeout=180)
    return {"status": "healthy", "timestamp": timestamp}
