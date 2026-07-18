from django.conf import settings


def application(request):
    return {"APP_NAME": settings.APP_NAME, "APP_VERSION": settings.APP_VERSION}
