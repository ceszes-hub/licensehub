from django.contrib.auth.models import Group, Permission


def ensure_license_roles(**kwargs):
    admin, _ = Group.objects.get_or_create(name="License Administrators")
    manager, _ = Group.objects.get_or_create(name="License Managers")
    reader, _ = Group.objects.get_or_create(name="License Readers")
    permissions = Permission.objects.filter(content_type__app_label="licenses")
    admin.permissions.set(permissions)
    manager.permissions.set(
        permissions.filter(
            codename__in=[
                "add_license",
                "change_license",
                "view_license",
                "add_licensedocument",
                "view_licensedocument",
                "delete_licensedocument",
                "export_license",
                "archive_license",
                "view_party",
            ]
        )
    )
    reader.permissions.set(
        permissions.filter(
            codename__in=["view_license", "view_licensedocument", "view_party", "export_license"]
        )
    )
