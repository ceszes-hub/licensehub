from datetime import timedelta
from io import StringIO
import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.core.models import SystemConfiguration
from apps.licenses.models import (
    License,
    LicenseDocument,
    NotificationLog,
    Party,
    PartyContact,
)
from apps.licenses.tasks import send_expiry_notifications
from apps.licenses.crypto import decrypt_secret
from apps.system.forms import BackupSettingsForm, NetworkSettingsForm
from apps.system.models import IntegrationSettings

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


def test_license_crud_keeps_reference_visible(client, admin):
    response = client.post("/licenses/new/", license_data())
    assert response.status_code == 302
    obj = License.objects.get()
    assert obj.secret_reference == "SECRET-123"
    assert client.get(f"/licenses/{obj.pk}/").status_code == 200
    assert client.get("/licenses/export.csv").status_code == 200


def test_license_document_upload_and_delete(client, admin, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    data = license_data()
    data["document_type"] = LicenseDocument.DocumentType.INSTALLATION_GUIDE
    data["documents"] = SimpleUploadedFile(
        "telepitesi-utmutato.pdf", b"example pdf content", content_type="application/pdf"
    )
    response = client.post("/licenses/new/", data)
    assert response.status_code == 302
    document = LicenseDocument.objects.get()
    assert document.document_type == LicenseDocument.DocumentType.INSTALLATION_GUIDE
    assert document.file.storage.exists(document.file.name)
    response = client.post(f"/licenses/{document.license_id}/documents/{document.pk}/delete/")
    assert response.status_code == 302
    assert not LicenseDocument.objects.exists()
    assert not document.file.storage.exists(document.file.name)


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
    manufacturer = Party.objects.get(kind=Party.Kind.MANUFACTURER)
    assert client.get(f"/licenses/manufacturers/{manufacturer.pk}/edit/").status_code == 200
    assert client.get("/licenses/distributors/").status_code == 200
    assert client.get("/licenses/documents/").status_code == 404
    assert client.get("/licenses/reports/").status_code == 200
    assert client.get("/audit/").status_code == 200
    assert client.get("/users/").status_code == 200
    assert client.get("/settings/").status_code == 200
    assert client.get("/settings/network/").status_code == 200
    assert client.get("/settings/ldap/").status_code == 200
    assert client.get("/settings/smtp/").status_code == 200
    assert client.post("/backup/", {"backup_now": "1"}).status_code == 302
    assert (tmp_path / ".backup-request").exists()


def test_backup_smb_settings_form_and_gui(client, admin, settings, tmp_path):
    settings.BACKUP_PATH = tmp_path
    data = {
        "backup_retention_days": 30,
        "backup_interval_hours": 12,
        "backup_destination": "SMB",
        "backup_local_subdirectory": "production",
        "backup_remote_path": "",
        "backup_smb_host": "192.168.0.50",
        "backup_smb_port": 445,
        "backup_smb_share": "Backups",
        "backup_smb_subdirectory": "LicenseHub",
        "backup_smb_domain": "LAUREL",
        "backup_smb_username": "licensebackup",
        "smb_password_input": "Strong-SMB-Password!",
        "save_settings": "1",
    }
    response = client.post("/backup/", data)
    assert response.status_code == 302
    config = IntegrationSettings.get_solo()
    assert config.backup_destination == "SMB"
    assert decrypt_secret(config.backup_smb_password) == "Strong-SMB-Password!"
    assert (tmp_path / ".rclone-runtime" / "host").read_text() == "192.168.0.50"
    assert (tmp_path / ".rclone-runtime" / "password").read_text() == "Strong-SMB-Password!"

    invalid = data | {"backup_smb_host": "", "backup_retention_days": 0}
    form = BackupSettingsForm(invalid, instance=config)
    assert not form.is_valid()
    assert "backup_smb_host" in form.errors
    assert "backup_retention_days" in form.errors


def test_network_settings_and_netplan_export(client, admin):
    data = {
        "network_hostname": "licensehub.example.local",
        "network_interface": "ens18",
        "network_address": "192.168.0.69/24",
        "network_gateway": "192.168.0.1",
        "network_dns_primary": "192.168.0.1",
        "network_dns_secondary": "1.1.1.1",
        "network_search_domain": "example.local",
        "network_public_url": "https://licensehub.example.local",
    }
    response = client.post("/settings/network/", data)
    assert response.status_code == 302
    output = StringIO()
    call_command("export_network_config", stdout=output)
    rendered = output.getvalue()
    assert "ens18:" in rendered
    assert "192.168.0.69/24" in rendered
    assert "via: 192.168.0.1" in rendered
    hostname = StringIO()
    call_command("export_network_hostname", stdout=hostname)
    assert hostname.getvalue().strip() == "licensehub.example.local"

    invalid = NetworkSettingsForm(data | {"network_address": "invalid"})
    assert not invalid.is_valid()
    assert "network_address" in invalid.errors

    config = IntegrationSettings.get_solo()
    config.network_dhcp = True
    config.save()
    output = StringIO()
    call_command("export_network_config", stdout=output)
    assert "dhcp4: true" in output.getvalue()
