import ipaddress

from django import forms
from apps.core.models import SystemConfiguration
from apps.licenses.crypto import encrypt_secret
from .models import IntegrationSettings


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemConfiguration
        fields = [
            "company_name",
            "company_short_name",
            "country",
            "timezone",
            "language",
            "support_email",
            "support_phone",
        ]
        labels = {
            "company_name": "Cégnév",
            "company_short_name": "Rövid név",
            "country": "Ország",
            "timezone": "Időzóna",
            "language": "Nyelv",
            "support_email": "Támogatási e-mail",
            "support_phone": "Támogatási telefon",
        }


class TestEmailForm(forms.Form):
    recipient = forms.EmailField(label="Teszt címzett")


class LDAPSettingsForm(forms.ModelForm):
    bind_password_input = forms.CharField(
        required=False, widget=forms.PasswordInput, label="Bind jelszó"
    )

    class Meta:
        model = IntegrationSettings
        fields = [
            "ldap_enabled",
            "ldap_server_uri",
            "ldap_use_ssl",
            "ldap_base_dn",
            "ldap_bind_dn",
            "ldap_user_filter",
            "ldap_admin_group",
            "ldap_manager_group",
            "ldap_reader_group",
        ]
        labels = {
            "ldap_enabled": "LDAP engedélyezve",
            "ldap_server_uri": "Szerver URI",
            "ldap_use_ssl": "TLS/SSL",
            "ldap_base_dn": "Base DN",
            "ldap_bind_dn": "Bind felhasználó",
            "ldap_user_filter": "Felhasználó szűrő",
            "ldap_admin_group": "Admin AD-csoport",
            "ldap_manager_group": "Licenckezelő AD-csoport",
            "ldap_reader_group": "Olvasó AD-csoport",
        }

    def save(self, commit=True):
        obj = super().save(False)
        if self.cleaned_data.get("bind_password_input"):
            obj.ldap_bind_password = encrypt_secret(self.cleaned_data["bind_password_input"])
        if commit:
            obj.save()
        return obj


class SMTPSettingsForm(forms.ModelForm):
    password_input = forms.CharField(
        required=False, widget=forms.PasswordInput, label="SMTP jelszó"
    )
    test_recipient = forms.EmailField(required=False, label="Teszt címzett")

    class Meta:
        model = IntegrationSettings
        fields = ["smtp_host", "smtp_port", "smtp_use_tls", "smtp_username", "smtp_from_email"]
        labels = {
            "smtp_host": "SMTP szerver",
            "smtp_port": "Port",
            "smtp_use_tls": "STARTTLS használata",
            "smtp_username": "Felhasználónév",
            "smtp_from_email": "Feladó e-mail",
        }

    def save(self, commit=True):
        obj = super().save(False)
        if self.cleaned_data.get("password_input"):
            obj.smtp_password = encrypt_secret(self.cleaned_data["password_input"])
        if commit:
            obj.save()
        return obj


class BackupSettingsForm(forms.ModelForm):
    smb_password_input = forms.CharField(
        required=False, widget=forms.PasswordInput, label="SMB jelszó"
    )

    class Meta:
        model = IntegrationSettings
        fields = [
            "backup_retention_days",
            "backup_interval_hours",
            "backup_destination",
            "backup_local_subdirectory",
            "backup_remote_path",
            "backup_smb_host",
            "backup_smb_port",
            "backup_smb_share",
            "backup_smb_subdirectory",
            "backup_smb_domain",
            "backup_smb_username",
        ]
        labels = {
            "backup_retention_days": "Megőrzési idő (nap)",
            "backup_interval_hours": "Mentési gyakoriság (óra)",
            "backup_destination": "Mentés célja",
            "backup_local_subdirectory": "Helyi alkönyvtár",
            "backup_remote_path": "Felhős rclone célútvonal",
            "backup_smb_host": "SMB szerver vagy IP-cím",
            "backup_smb_port": "SMB port",
            "backup_smb_share": "Megosztás neve",
            "backup_smb_subdirectory": "SMB alkönyvtár",
            "backup_smb_domain": "Tartomány",
            "backup_smb_username": "SMB felhasználónév",
        }

    def clean_backup_retention_days(self):
        value = self.cleaned_data["backup_retention_days"]
        if not 1 <= value <= 3650:
            raise forms.ValidationError("A megőrzési idő 1 és 3650 nap között legyen.")
        return value

    def clean_backup_interval_hours(self):
        value = self.cleaned_data["backup_interval_hours"]
        if not 1 <= value <= 8760:
            raise forms.ValidationError("A gyakoriság 1 és 8760 óra között legyen.")
        return value

    def clean(self):
        cleaned = super().clean()
        destination = cleaned.get("backup_destination")
        if destination == IntegrationSettings.BackupDestination.SMB:
            for field in ("backup_smb_host", "backup_smb_share", "backup_smb_username"):
                if not cleaned.get(field):
                    self.add_error(field, "SMB mentésnél ez a mező kötelező.")
        elif destination != IntegrationSettings.BackupDestination.LOCAL and not cleaned.get(
            "backup_remote_path"
        ):
            self.add_error("backup_remote_path", "Felhős mentésnél a célútvonal kötelező.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(False)
        if self.cleaned_data.get("smb_password_input"):
            obj.backup_smb_password = encrypt_secret(self.cleaned_data["smb_password_input"])
        if commit:
            obj.save()
        return obj


class NetworkSettingsForm(forms.ModelForm):
    class Meta:
        model = IntegrationSettings
        fields = [
            "network_hostname",
            "network_interface",
            "network_dhcp",
            "network_address",
            "network_gateway",
            "network_dns_primary",
            "network_dns_secondary",
            "network_search_domain",
            "network_public_url",
        ]
        labels = {
            "network_hostname": "Gépnév",
            "network_interface": "Hálózati interfész",
            "network_dhcp": "DHCP használata",
            "network_address": "IP-cím/prefix",
            "network_gateway": "Alapértelmezett átjáró",
            "network_dns_primary": "Elsődleges DNS",
            "network_dns_secondary": "Másodlagos DNS",
            "network_search_domain": "Keresési tartomány",
            "network_public_url": "LicenseHub publikus URL",
        }

    def clean_network_hostname(self):
        value = self.cleaned_data["network_hostname"].strip().lower()
        labels = value.split(".") if value else []
        if value and any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or not label.replace("-", "").isalnum()
            for label in labels
        ):
            raise forms.ValidationError("Érvénytelen gépnév.")
        return value

    def clean_network_interface(self):
        value = self.cleaned_data["network_interface"]
        if not value.replace("-", "").replace("_", "").isalnum():
            raise forms.ValidationError("Érvénytelen interfésznév.")
        return value

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("network_dhcp"):
            address = cleaned.get("network_address")
            if not address:
                self.add_error("network_address", "Statikus beállításnál kötelező.")
            else:
                try:
                    ipaddress.ip_interface(address)
                except ValueError:
                    self.add_error("network_address", "Érvénytelen IP-cím vagy prefix.")
            if not cleaned.get("network_gateway"):
                self.add_error("network_gateway", "Statikus beállításnál kötelező.")
        return cleaned
