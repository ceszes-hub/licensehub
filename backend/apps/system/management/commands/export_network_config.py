from django.core.management.base import BaseCommand, CommandError

from apps.system.models import IntegrationSettings


class Command(BaseCommand):
    help = "Export the validated LicenseHub Netplan configuration"

    def handle(self, *args, **options):
        config = IntegrationSettings.get_solo()
        interface = config.network_interface
        if not interface.replace("-", "").replace("_", "").isalnum():
            raise CommandError("Invalid network interface")
        lines = ["network:", "  version: 2", "  ethernets:", f"    {interface}:"]
        if config.network_dhcp:
            lines.append("      dhcp4: true")
        else:
            if not config.network_address or not config.network_gateway:
                raise CommandError("Static address and gateway are required")
            lines.extend(
                [
                    "      dhcp4: false",
                    "      addresses:",
                    f"        - {config.network_address}",
                    "      routes:",
                    "        - to: default",
                    f"          via: {config.network_gateway}",
                ]
            )
            dns = [
                str(value)
                for value in (config.network_dns_primary, config.network_dns_secondary)
                if value
            ]
            if dns:
                lines.extend(["      nameservers:", f"        addresses: [{', '.join(dns)}]"])
                if config.network_search_domain:
                    lines.append(f"        search: [{config.network_search_domain}]")
        self.stdout.write("\n".join(lines))
