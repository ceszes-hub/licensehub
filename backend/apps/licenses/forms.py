from django import forms
from .crypto import encrypt_secret
from .models import License, LicenseDocument


class LicenseForm(forms.ModelForm):
    license_reference = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        label="Licenckulcs vagy szerzÅ‘dÃ©sszÃ¡m",
    )
    notification_intervals_text = forms.CharField(
        required=False, initial="180,90,60,30,14,7", label="Ã‰rtesÃ­tÃ©si napok"
    )
    notification_emails_text = forms.CharField(
        required=False, label="Ã‰rtesÃ­tÃ©si e-mailek", help_text="VesszÅ‘vel elvÃ¡lasztva"
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
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "expires_at": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
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
            raise forms.ValidationError(
                "Csak vesszÅ‘vel elvÃ¡lasztott egÃ©sz napÃ©rtÃ©kek adhatÃ³k meg."
            )
        if any(v < 1 or v > 3650 for v in values):
            raise forms.ValidationError("Az intervallum 1 Ã©s 3650 nap kÃ¶zÃ¶tti legyen.")
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
            obj.secret_reference = encrypt_secret(self.cleaned_data["license_reference"])
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class DocumentForm(forms.ModelForm):
    class Meta:
        model = LicenseDocument
        fields = ["file"]

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > 20 * 1024 * 1024:
            raise forms.ValidationError("A fÃ¡jl legfeljebb 20 MB lehet.")
        allowed = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".lic", ".zip")
        if not f.name.lower().endswith(allowed):
            raise forms.ValidationError("Nem engedélyezett fájltípus.")
        return f
