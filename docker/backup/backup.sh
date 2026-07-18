#!/bin/sh
set -eu

backup_root="${BACKUP_PATH:-/backups}"
retention_days="${BACKUP_RETENTION_DAYS:-14}"
interval_seconds="${BACKUP_INTERVAL_SECONDS:-86400}"
destination="LOCAL"
local_subdirectory="full"
remote_path=""

load_backup_settings() {
    row=$(PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F '|' \
        -c "SELECT backup_retention_days, backup_interval_hours, backup_destination, backup_local_subdirectory, backup_remote_path FROM system_integrationsettings ORDER BY id LIMIT 1" \
        2>/dev/null || true)
    if [ -n "$row" ]; then
        IFS='|' read -r retention_days interval_hours destination local_subdirectory remote_path <<EOF
$row
EOF
        interval_seconds=$((interval_hours * 3600))
    fi
    case "$local_subdirectory" in
        ""|*[!A-Za-z0-9._-]*) local_subdirectory="full" ;;
    esac
}

run_backup() {
    load_backup_settings
    target_dir="$backup_root/$local_subdirectory"
    mkdir -p "$target_dir"
    stamp=$(date -u +%Y%m%dT%H%M%SZ)
    name="licensehub_full_${stamp}"
    workdir=$(mktemp -d)
    trap 'rm -rf "$workdir"' EXIT INT TERM

    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -Fc -f "$workdir/database.dump"
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dumpall \
        -h "$POSTGRES_HOST" -U "$POSTGRES_USER" --globals-only \
        > "$workdir/globals.sql"
    tar -C /media -czf "$workdir/media.tar.gz" .
    tar -C /source -czf "$workdir/config.tar.gz" \
        .env compose.yaml docker/nginx/nginx.conf docker/nginx/certs docker/backup/rclone

    {
        echo "format=licensehub-full-backup-v1"
        echo "created_utc=$stamp"
        echo "database=$POSTGRES_DB"
        echo "postgres_user=$POSTGRES_USER"
        echo "destination=$destination"
        echo "includes=database,roles,media,environment,compose,nginx,tls"
    } > "$workdir/manifest.txt"
    (cd "$workdir" && sha256sum database.dump globals.sql media.tar.gz config.tar.gz manifest.txt > checksums.sha256)

    bundle="$target_dir/${name}.tar.gz"
    tar -C "$workdir" -czf "$bundle" \
        database.dump globals.sql media.tar.gz config.tar.gz manifest.txt checksums.sha256
    chmod 600 "$bundle"
    (cd "$target_dir" && sha256sum "${name}.tar.gz" > "${name}.tar.gz.sha256")
    chmod 600 "$bundle.sha256"

    find "$backup_root" -name 'licensehub_full_*.tar.gz*' -mtime "+$retention_days" -delete
    if [ "$destination" != "LOCAL" ]; then
        [ -n "$remote_path" ] || { echo "Cloud destination is selected but remote path is empty." >&2; exit 4; }
        rclone copyto "$bundle" "$remote_path/${name}.tar.gz"
        rclone copyto "$bundle.sha256" "$remote_path/${name}.tar.gz.sha256"
        rclone delete "$remote_path" --min-age "${retention_days}d" --include 'licensehub_full_*.tar.gz*'
    fi
    echo "full backup completed: $bundle"
    rm -rf "$workdir"
    trap - EXIT INT TERM
}

[ "${1:-}" = once ] && { run_backup; exit; }
next=0
while :; do
    now=$(date +%s)
    if [ -f "$backup_root/.backup-request" ] || [ "$now" -ge "$next" ]; then
        rm -f "$backup_root/.backup-request"
        run_backup
        next=$((now + interval_seconds))
    fi
    sleep 10
done