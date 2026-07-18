import pytest
from django.contrib.auth import get_user_model
from apps.audit.models import AuditEvent
from apps.core.models import SystemConfiguration

pytestmark = pytest.mark.django_db


def admin_data(password="VeryStrong!Password42", confirm=None):
    return {
        "org-company_name": "Acme Kft",
        "org-company_short_name": "Acme",
        "org-country": "HU",
        "org-timezone": "Europe/Budapest",
        "org-language": "hu",
        "org-support_email": "support@example.com",
        "org-support_phone": "",
        "admin-username": "root",
        "admin-first_name": "Ada",
        "admin-last_name": "Admin",
        "admin-email": "admin@example.com",
        "admin-password": password,
        "admin-password_confirm": confirm or password,
    }


def test_setup_available_and_creates_admin(client):
    assert client.get("/setup/").status_code == 200
    response = client.post("/setup/", admin_data())
    assert response.status_code == 302
    user = get_user_model().objects.get(username="root")
    assert user.is_superuser and user.is_staff and user.is_active
    assert user.password.startswith("argon2$")
    assert SystemConfiguration.objects.get().setup_completed
    assert AuditEvent.objects.filter(event_type="SETUP_COMPLETED").exists()
    assert client.get("/setup/").status_code == 403


def test_setup_rejects_password_mismatch_and_weak_password(client):
    assert client.post("/setup/", admin_data("short", "different")).status_code == 200
    assert not get_user_model().objects.exists()


def test_auth_login_logout_and_lockout(client, settings):
    user = get_user_model().objects.create_user(username="alice", password="VeryStrong!Password42")
    SystemConfiguration.objects.create(
        company_name="A", company_short_name="A", support_email="a@b.hu", setup_completed=True
    )
    assert (
        client.post(
            "/login/", {"username": "alice", "password": "VeryStrong!Password42"}
        ).status_code
        == 302
    )
    assert client.post("/logout/").status_code == 302
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        client.post("/login/", {"username": "alice", "password": "bad"})
    user.refresh_from_db()
    assert user.locked_until is not None
    assert (
        client.post(
            "/login/", {"username": "alice", "password": "VeryStrong!Password42"}
        ).status_code
        == 200
    )


def test_inactive_user_cannot_login(client):
    get_user_model().objects.create_user(
        username="off", password="VeryStrong!Password42", is_active=False
    )
    SystemConfiguration.objects.create(
        company_name="A", company_short_name="A", support_email="a@b.hu", setup_completed=True
    )
    assert (
        client.post("/login/", {"username": "off", "password": "VeryStrong!Password42"}).status_code
        == 200
    )


def test_health_and_permissions(client):
    assert client.get("/health/").json() == {"status": "healthy"}
    SystemConfiguration.objects.create(
        company_name="A", company_short_name="A", support_email="a@b.hu", setup_completed=True
    )
    assert client.get("/system/health/").status_code == 302
    user = get_user_model().objects.create_user(username="u", password="VeryStrong!Password42")
    client.force_login(user)
    assert client.get("/system/health/").status_code == 302
    user.is_staff = True
    user.save()
    assert client.get("/system/health/").status_code == 200


def test_singleton_configuration():
    SystemConfiguration.objects.create(
        company_name="A", company_short_name="A", support_email="a@b.hu"
    )
    with pytest.raises(Exception):
        SystemConfiguration.objects.create(
            company_name="B", company_short_name="B", support_email="b@b.hu"
        )
