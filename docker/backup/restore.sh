#!/bin/sh
set -eu

bundle_name="${1:-}"
case "$bundle_name" in
    licensehub_full_*.tar.gz) ;;
    *) echo "Invalid backup name: $bundle_name" >&2; exit 2 ;;
esac
[ "$bundle_name" = "$(basename "$bundle_name")" ] || { echo "Only a backup file name is allowed." >&2; exit 2; }

backup_root="${BACKUP_PATH:-/backups}"
bundle=$(find "$backup_root" -type f -name "$bundle_name" -print -quit)
[ -n "$bundle" ] && [ -f "$bundle" ] || { echo "Backup not found: $bundle_name" >&2; exit 3; }
[ -f "$bundle.sha256" ] || { echo "Outer checksum not found." >&2; exit 3; }
bundle_dir=$(dirname "$bundle")
(cd "$bundle_dir" && sha256sum -c "$bundle_name.sha256")

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT INT TERM
tar -C "$workdir" -xzf "$bundle"
(cd "$workdir" && sha256sum -c checksums.sha256)
grep -q '^format=licensehub-full-backup-v1$' "$workdir/manifest.txt"

PGPASSWORD="$POSTGRES_PASSWORD" dropdb \
    -h "$POSTGRES_HOST" -U "$POSTGRES_USER" --force --if-exists "$POSTGRES_DB"
PGPASSWORD="$POSTGRES_PASSWORD" createdb \
    -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB"
PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
    -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --no-owner --role="$POSTGRES_USER" "$workdir/database.dump"

find /media -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
tar -C /media -xzf "$workdir/media.tar.gz"

# Restore database roles/passwords last so the restored .env remains in sync.
PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -f "$workdir/globals.sql" >/dev/null 2>&1 || true

if [ -d /restore-target ]; then
    tar -C /restore-target -xzf "$workdir/config.tar.gz"
fi

echo "full restore completed from: $bundle"