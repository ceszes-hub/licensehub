from celery import shared_task
from .views import checks


@shared_task
def periodic_health_check():
    return checks()
