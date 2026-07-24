from typing import Any

from django import forms
from django.forms import inlineformset_factory
from .models import License, LicenseDocument, Party, PartyContact


class LicenseForm(forms.ModelForm):
    license_reference = forms.CharField(
        required=False,
        widget=forms.TextInput(),
        label="Licenckulcs vagy szerződésszám",
    )
    notification_intervals_text = forms.CharField(
        required=False, initial="180,90,60,30,14,7", label="Értesítési napok"
    )
    notification_emails_text = forms.CharField(
        required=False, label="Értesítési e-mailek", help_text="Vesszővel elválasztva"
    )

    class Meta:
        model = License
        exclude = [
            "secret_reference",
            "notification_intervals",
            "notification_emails",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        labels = {
            "reference_code": "Licencazonosító",
            "name": "Elnevezés",
            "manufacturer": "Gyártó",
            "distributor": "Disztribútor",
            "quantity": "Darabszám",
            "used_quantity": "Felhasznált darabszám",
            "organization": "Szervezet",
            "deployment_mode": "Telepítési mód",
            "concurrent": "Konkurens használatú",
            "concurrent_limit": "Konkurens használati limit",
            "license_type": "Licenctípus",
            "purchase_date": "Vásárlás dátuma",
            "valid_from": "Érvényesség kezdete",
            "expires_at": "Lejárat dátuma",
            "auto_renews": "Automatikusan megújul",
            "notification_users": "Értesítendő személyek",
            "cost": "Költség",
            "currency": "Pénznem",
            "cost_center": "Költséghely",
            "owner": "Felelős személy",
            "status": "Státusz",
            "notes": "Megjegyzés",
        }
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "expires_at": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["license_reference"].initial = self.instance.secret_reference
            self.fields["notification_intervals_text"].initial = ",".join(
                map(str, self.instance.notification_intervals)
            )
            self.fields["notification_emails_text"].initial = ",".join(
                self.instance.notification_emails
            )

    def clean_notification_intervals_text(self):
        raw = self.cleaned_data.get("notification_intervals_text", "")
        try:
            values = sorted({int(v.strip()) for v in raw.split(",") if v.strip()}, reverse=True)
        except ValueError:
            raise forms.ValidationError("Csak vesszővel elválasztott egész napértékek adhatók meg.")
        if any(v < 1 or v > 3650 for v in values):
            raise forms.ValidationError("Az intervallum 1 és 3650 nap közötti legyen.")
        return values

    def clean_notification_emails_text(self):
        values = [
            v.strip().lower()
            for v in self.cleaned_data.get("notification_emails_text", "").split(",")
            if v.strip()
        ]
        validator = forms.EmailField()
        for value in values:
            validator.clean(value)
        return values

    def save(self, commit=True):
        obj = super().save(False)
        obj.notification_intervals = self.cleaned_data["notification_intervals_text"]
        obj.notification_emails = self.cleaned_data["notification_emails_text"]
        if self.cleaned_data.get("license_reference"):
            obj.secret_reference = self.cleaned_data["license_reference"]
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class DocumentForm(forms.ModelForm):
    class Meta:
        model = LicenseDocument
        fields = ["document_type", "file"]

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > 20 * 1024 * 1024:
            raise forms.ValidationError("A fájl legfeljebb 20 MB lehet.")
        allowed = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".lic", ".zip")
        if not f.name.lower().endswith(allowed):
            raise forms.ValidationError("Nem engedélyezett fájltípus.")
        return f


class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ["name", "postal_code", "address", "active"]
        labels = {
            "name": "Név",
            "postal_code": "Irányítószám",
            "address": "Cím",
            "active": "Aktív",
        }


PartyContactFormSet: Any = inlineformset_factory(
    Party,
    PartyContact,
    fields=["name", "position", "email", "phone", "active"],
    labels={
        "name": "Kapcsolattartó neve",
        "position": "Beosztás",
        "email": "E-mail-cím",
        "phone": "Telefonszám",
        "active": "Aktív",
    },
    extra=1,
    can_delete=True,
)
