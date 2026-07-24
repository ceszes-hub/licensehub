from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("licenses", "0004_unmask_license_references")]

    operations = [
        migrations.AddField(
            model_name="license",
            name="reference_code",
            field=models.CharField(blank=True, db_index=True, max_length=50),
        ),
        migrations.AddField(
            model_name="license",
            name="organization",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="license",
            name="used_quantity",
            field=models.PositiveIntegerField(blank=True, default=0),
        ),
    ]
