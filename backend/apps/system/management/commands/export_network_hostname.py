from django.core.management.base import BaseCommand

from apps.system.models import IntegrationSettings


class Command(BaseCommand):
    help = "Export the validated LicenseHub host name"

    def handle(self, *args, **options):
        config = IntegrationSettings.get_solo()
        self.stdout.write(config.network_hostname)
