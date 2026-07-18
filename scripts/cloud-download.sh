#!/bin/sh
set -eu

remote_path="${1:-}"
backup_name="${2:-}"
case "$backup_name" in licensehub_full_*.tar.gz) ;; *) echo "Usage: bash scripts/cloud-download.sh remote:path licensehub_full_TIMESTAMP.tar.gz" >&2; exit 2 ;; esac
[ -n "$remote_path" ] || { echo "Remote path is required." >&2; exit 2; }

docker compose run --rm --no-deps --entrypoint rclone backup \
    copyto "$remote_path/$backup_name" "/backups/full/$backup_name"
docker compose run --rm --no-deps --entrypoint rclone backup \
    copyto "$remote_path/$backup_name.sha256" "/backups/full/$backup_name.sha256"
docker compose run --rm --no-deps --entrypoint /bin/sh backup \
    -c "cd /backups/full && sha256sum -c '$backup_name.sha256'"
echo "Cloud backup downloaded and verified: $backup_name"