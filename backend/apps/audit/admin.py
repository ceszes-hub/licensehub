from django.contrib import admin
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditAdmin(admin.ModelAdmin):
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_add_permission(self, r):
        return False

    def has_delete_permission(self, r, obj=None):
        return False
