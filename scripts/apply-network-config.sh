#!/bin/sh
set -eu

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo: sudo bash scripts/apply-network-config.sh" >&2; exit 1; }
command -v netplan >/dev/null 2>&1 || { echo "netplan is not installed." >&2; exit 1; }

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
target=/etc/netplan/99-licensehub.yaml
backup_dir="/var/backups/licensehub-netplan/$(date +%Y%m%dT%H%M%S)"
mkdir -p "$backup_dir"
if [ -d /etc/netplan ]; then
    cp -a /etc/netplan/. "$backup_dir/"
fi

tmp=$(mktemp /etc/netplan/.licensehub.XXXXXX)
trap 'rm -f "$tmp"' EXIT INT TERM
docker compose exec -T web python manage.py export_network_config > "$tmp"
chmod 600 "$tmp"
cp "$tmp" "$target"
netplan generate

echo "Configuration validated. Netplan will roll back after 120 seconds unless confirmed."
netplan try --timeout 120
echo "Network configuration accepted. Previous files: $backup_dir"