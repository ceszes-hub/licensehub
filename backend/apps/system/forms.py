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
