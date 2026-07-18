#!/bin/bash
set -Eeuo pipefail
dump=${1:-}; [[ -f "$dump" ]] || { echo 'Usage: scripts/restore.sh DUMP_FILE'; exit 2; }; [[ -f "$dump.sha256" ]] || { echo 'Missing checksum file'; exit 2; }; (cd "$(dirname "$dump")" && sha256sum -c "$(basename "$dump").sha256")
read -r -p 'This replaces the database. Type RESTORE: ' answer; [[ "$answer" == RESTORE ]] || exit 1
./scripts/backup.sh
docker compose stop web celery-worker celery-beat
docker compose exec -T postgres sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" dropdb -U "$POSTGRES_USER" "$POSTGRES_DB" && PGPASSWORD="$POSTGRES_PASSWORD" createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T postgres sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < "$dump"
docker compose start web celery-worker celery-beat
docker compose exec -T web python manage.py migrate --noinput
./scripts/healthcheck.sh
