from django.db import migrations


def decrypt_references(apps, schema_editor):
    from apps.licenses.crypto import decrypt_secret

    License = apps.get_model("licenses", "License")
    for license_obj in License.objects.exclude(secret_reference="").iterator():
        decrypted = decrypt_secret(license_obj.secret_reference)
        if decrypted:
            license_obj.secret_reference = decrypted
            license_obj.save(update_fields=["secret_reference"])


def encrypt_references(apps, schema_editor):
    from apps.licenses.crypto import encrypt_secret

    License = apps.get_model("licenses", "License")
    for license_obj in License.objects.exclude(secret_reference="").iterator():
        license_obj.secret_reference = encrypt_secret(license_obj.secret_reference)
        license_obj.save(update_fields=["secret_reference"])


class Migration(migrations.Migration):
    dependencies = [("licenses", "0003_licensedocument_document_type")]
    operations = [migrations.RunPython(decrypt_references, encrypt_references)]
