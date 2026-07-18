from rest_framework import serializers
from .models import License, Party
class PartySerializer(serializers.ModelSerializer):
    class Meta: model=Party; fields=["id","name","kind"]
class LicenseSerializer(serializers.ModelSerializer):
    manufacturer_name=serializers.CharField(source="manufacturer.name",read_only=True); distributor_name=serializers.CharField(source="distributor.name",read_only=True); days_until_expiry=serializers.IntegerField(read_only=True)
    class Meta:
        model=License
        exclude=["secret_reference","notification_emails"]
        read_only_fields=["created_by","updated_by","created_at","updated_at"]
