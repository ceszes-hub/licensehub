from django import forms
from django.contrib.auth import get_user_model, password_validation


class OrganizationForm(forms.Form):
    company_name = forms.CharField(max_length=200, label="C?gn?v")
    company_short_name = forms.CharField(max_length=50, label="R?vid n?v")
    country = forms.CharField(max_length=2, initial="HU")
    timezone = forms.CharField(initial="Europe/Budapest")
    language = forms.CharField(initial="hu")
    support_email = forms.EmailField()
    support_phone = forms.CharField(required=False)


class AdminForm(forms.Form):
    username = forms.CharField()
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        d = super().clean()
        if d.get("password") != d.get("password_confirm"):
            self.add_error("password_confirm", "A jelszavak nem egyeznek.")
        user = get_user_model()(username=d.get("username"), email=d.get("email"))
        if d.get("password"):
            try:
                password_validation.validate_password(d["password"], user)
            except forms.ValidationError as e:
                self.add_error("password", e)
        return d
