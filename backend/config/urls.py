from django.contrib import admin
from django.urls import include, path
from apps.accounts.views import LoginView, logout_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("setup/", include("apps.core.setup_urls")),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("", include("apps.system.urls")),
]
