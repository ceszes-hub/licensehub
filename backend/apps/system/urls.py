from django.urls import path
from . import views

urlpatterns = [
    path("audit/", views.audit_log, name="audit_log"),
    path("users/", views.user_list, name="user_list"),
    path("settings/", views.settings_view, name="settings"),
    path("settings/network/", views.network_settings, name="network_settings"),
    path("settings/ldap/", views.ldap_status, name="ldap_status"),
    path("settings/smtp/", views.smtp_test, name="smtp_test"),
    path("backup/", views.backup_dashboard, name="backup_dashboard"),
    path("", views.dashboard, name="dashboard"),
    path("health/", views.health, name="health"),
    path("system/health/", views.system_health, name="system_health"),
]
