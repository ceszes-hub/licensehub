from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from .forms import OrganizationForm, AdminForm
from .models import SystemConfiguration
from apps.audit.services import record_event


def setup(request):
    User = get_user_model()
    if (
        User.objects.filter(is_superuser=True).exists()
        or SystemConfiguration.objects.filter(setup_completed=True).exists()
    ):
        return render(request, "setup/locked.html", status=403)
    org = OrganizationForm(request.POST or None, prefix="org")
    admin = AdminForm(request.POST or None, prefix="admin")
    if request.method == "POST" and org.is_valid() and admin.is_valid():
        with transaction.atomic():
            a = admin.cleaned_data
            user = User.objects.create_superuser(
                username=a["username"],
                email=a["email"],
                password=a["password"],
                first_name=a["first_name"],
                last_name=a["last_name"],
            )
            o = org.cleaned_data
            SystemConfiguration.objects.create(
                **o, setup_completed=True, installation_date=timezone.now(), first_admin=user
            )
            record_event("FIRST_ADMIN_CREATED", request, user, "First administrator created")
            record_event("SETUP_COMPLETED", request, user, "Setup completed")
        login(request, user)
        return redirect("dashboard")
    return render(request, "setup/setup.html", {"org_form": org, "admin_form": admin})
