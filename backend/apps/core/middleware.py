from django.shortcuts import redirect
from .models import SystemConfiguration


class SetupRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed = ("/setup/", "/health/", "/static/", "/media/", "/admin/", "/login/")
        configured = SystemConfiguration.objects.filter(setup_completed=True).exists()
        if not configured and not request.path.startswith(allowed):
            return redirect("setup")
        return self.get_response(request)
