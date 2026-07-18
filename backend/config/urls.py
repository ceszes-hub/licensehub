from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.accounts.views import LoginView, logout_view
from apps.licenses.api import LicenseViewSet, PartyViewSet

router = DefaultRouter()
router.register("licenses", LicenseViewSet)
router.register("parties", PartyViewSet)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("setup/", include("apps.core.setup_urls")),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_view, name="logout"),
    path("licenses/", include("apps.licenses.urls")),
    path("api/v1/", include(router.urls)),
    path("", include("apps.system.urls")),
]
