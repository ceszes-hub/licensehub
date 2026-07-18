from django import forms
from apps.core.models import SystemConfiguration


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
