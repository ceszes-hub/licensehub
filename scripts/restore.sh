#!/bin/sh
set -eu

backup_name="${1:-}"
if [ -z "$backup_name" ]; then
    echo "Usage: ./scripts/restore.sh licensehub_full_YYYYMMDDTHHMMSSZ.tar.gz" >&2
    echo "Available backups:" >&2
    docker compose exec -T backup find /backups -name 'licensehub_full_*.tar.gz' -exec basename {} \\; 2>/dev/null || true
    exit 2
fi
case "$backup_name" in licensehub_full_*.tar.gz) ;; *) echo "Invalid backup name." >&2; exit 2 ;; esac

printf 'This replaces the current database, uploaded files and local configuration. Type RESTORE: '
read -r confirmation
[ "$confirmation" = "RESTORE" ] || { echo "Restore cancelled."; exit 1; }

project_dir=$(pwd)
docker compose stop nginx web celery-worker celery-beat backup
docker compose up -d postgres
docker compose run --rm --no-deps \
    -v "$project_dir:/restore-target" \
    --entrypoint /bin/sh backup /restore.sh "$backup_name"
docker compose up -d --build
docker compose exec -T web python manage.py migrate
docker compose exec -T web python manage.py collectstatic --clear --noinput
docker compose restart nginx celery-worker celery-beat backup
docker compose ps