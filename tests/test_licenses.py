from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import SystemConfiguration
from apps.licenses.crypto import decrypt_secret
from apps.licenses.models import License, NotificationLog, Party, PartyContact
from apps.licenses.tasks import send_expiry_notifications

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(client):
    user = get_user_model().objects.create_superuser(
        "admin", "admin@example.com", "VeryStrong!Password42"
    )
    client.force_login(user)
    SystemConfiguration.objects.create(
        company_name="A",
        company_short_name="A",
        support_email="a@example.com",
        setup_completed=True,
    )
    return user


def license_data():
    return {
        "name": "SQL Server",
        "quantity": 50,
        "deployment_mode": "ON_PREMISES",
        "license_type": "SUBSCRIPTION",
        "status": "ACTIVE",
        "currency": "HUF",
        "notification_intervals_text": "30,14,7",
        "notification_emails_text": "owner@example.com",
        "license_reference": "SECRET-123",
        "expires_at": (timezone.localdate() + timedelta(days=30)).isoformat(),
    }


def test_license_crud_encrypts_secret(client, admin):
    response = client.post("/licenses/new/", license_data())
    assert response.status_code == 302
    obj = License.objects.get()
    assert "SECRET-123" not in obj.secret_reference
    assert decrypt_secret(obj.secret_reference) == "SECRET-123"
    assert client.get(f"/licenses/{obj.pk}/").status_code == 200
    assert client.get("/licenses/export.csv").status_code == 200


def test_concurrent_limit_validation():
    obj = License(
        name="Concurrent",
        quantity=1,
        deployment_mode="CLOUD",
        license_type="OTHER",
        concurrent=True,
    )
    with pytest.raises(ValidationError):
        obj.full_clean()


def test_expiry_notification(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "licensehub@example.com"
    obj = License.objects.create(
        name="SQL Server",
        quantity=50,
        deployment_mode="ON_PREMISES",
        license_type="SUBSCRIPTION",
        expires_at=timezone.localdate() + timedelta(days=30),
        notification_intervals=[30],
        notification_emails=["owner@example.com"],
    )
    assert send_expiry_notifications()["sent"] == 1
    assert len(mail.outbox) == 1
    assert NotificationLog.objects.get(license=obj).success
    assert send_expiry_notifications()["sent"] == 0


def test_distributor_with_multiple_contacts(client, admin):
    response = client.post(
        "/licenses/distributors/new/",
        {
            "name": "Example Kft.",
            "postal_code": "1111",
            "address": "Budapest, Példa utca 1.",
            "active": "on",
            "contacts-TOTAL_FORMS": "2",
            "contacts-INITIAL_FORMS": "0",
            "contacts-MIN_NUM_FORMS": "0",
            "contacts-MAX_NUM_FORMS": "1000",
            "contacts-0-name": "Kiss Péter",
            "contacts-0-position": "Értékesítő",
            "contacts-0-email": "peter@example.com",
            "contacts-0-phone": "+36 1 234 5678",
            "contacts-0-active": "on",
            "contacts-1-name": "Nagy Anna",
            "contacts-1-position": "Ügyfélszolgálat",
            "contacts-1-email": "anna@example.com",
            "contacts-1-phone": "+36 30 123 4567",
            "contacts-1-active": "on",
        },
    )
    assert response.status_code == 302
    distributor = Party.objects.get(kind=Party.Kind.DISTRIBUTOR)
    assert distributor.postal_code == "1111"
    assert distributor.contacts.count() == 2
    assert PartyContact.objects.filter(party=distributor, name="Nagy Anna").exists()


def test_party_unique():
    Party.objects.create(name="Microsoft", kind="MANUFACTURER")
    with pytest.raises(Exception):
        Party.objects.create(name="Microsoft", kind="MANUFACTURER")


def test_license_list_edit_duplicate_archive(client, admin):
    obj = License.objects.create(
        name="App",
        quantity=1,
        deployment_mode="CLOUD",
        license_type="OTHER",
        created_by=admin,
        updated_by=admin,
    )
    assert client.get("/licenses/?q=App&status=ACTIVE").status_code == 200
    data = license_data()
    data["name"] = "Changed"
    assert client.post(f"/licenses/{obj.pk}/edit/", data).status_code == 302
    assert client.get(f"/licenses/{obj.pk}/duplicate/").status_code == 302
    assert License.objects.count() == 2
    assert client.post(f"/licenses/{obj.pk}/archive/").status_code == 302
    obj.refresh_from_db()
    assert obj.status == License.Status.ARCHIVED


def test_ldap_backend_disabled(settings):
    from apps.accounts.ldap_backend import LDAPBackend

    settings.LDAP_ENABLED = False
    assert LDAPBackend().authenticate(None, username="u", password="p") is None
    assert LDAPBackend().get_user(999999) is None


def test_management_pages(client, admin, settings, tmp_path):
    settings.BACKUP_PATH = tmp_path
    assert (
        client.post(
            "/licenses/manufacturers/new/", {"name": "Microsoft", "active": True}
        ).status_code
        == 302
    )
    assert client.get("/licenses/manufacturers/").status_code == 200
    assert client.get("/licenses/distributors/").status_code == 200
    assert client.get("/licenses/documents/").status_code == 200
    assert client.get("/licenses/reports/").status_code == 200
    assert client.get("/audit/").status_code == 200
    assert client.get("/users/").status_code == 200
    assert client.get("/settings/").status_code == 200
    assert client.get("/settings/ldap/").status_code == 200
    assert client.get("/settings/smtp/").status_code == 200
    assert client.post("/backup/").status_code == 302
    assert (tmp_path / ".backup-request").exists()
