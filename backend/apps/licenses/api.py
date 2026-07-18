from rest_framework.permissions import DjangoModelPermissions
from rest_framework.viewsets import ModelViewSet
from .models import License, Party
from .serializers import LicenseSerializer, PartySerializer
class LicenseViewSet(ModelViewSet):
    queryset=License.objects.select_related("manufacturer","distributor","owner"); serializer_class=LicenseSerializer; permission_classes=[DjangoModelPermissions]; filterset_fields=[]; search_fields=["name"]
    def perform_create(self,serializer): serializer.save(created_by=self.request.user,updated_by=self.request.user)
    def perform_update(self,serializer): serializer.save(updated_by=self.request.user)
class PartyViewSet(ModelViewSet):
    queryset=Party.objects.all(); serializer_class=PartySerializer; permission_classes=[DjangoModelPermissions]
