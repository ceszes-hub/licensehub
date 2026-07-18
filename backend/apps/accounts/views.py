from django.contrib.auth import views as auth_views, logout
from django.shortcuts import redirect
from apps.audit.services import record_event


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        record_event("LOGIN_SUCCESS", self.request, self.request.user, "Successful login")
        return response

    def form_invalid(self, form):
        record_event("LOGIN_FAILED", self.request, None, "Failed login", False)
        return super().form_invalid(form)


def logout_view(request):
    record_event(
        "LOGOUT", request, request.user if request.user.is_authenticated else None, "Logout"
    )
    logout(request)
    return redirect("login")
