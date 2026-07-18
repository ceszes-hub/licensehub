from django.contrib import admin
from .models import License, LicenseDocument, NotificationLog, Party
admin.site.register(Party)
admin.site.register(License)
admin.site.register(LicenseDocument)
@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    readonly_fields=[f.name for f in NotificationLog._meta.fields]
    def has_add_permission(self,request): return False
    def has_delete_permission(self,request,obj=None): return False
