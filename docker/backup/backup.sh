#!/bin/sh
set -eu
run_backup(){ stamp=$(date -u +%Y%m%dT%H%M%SZ); file="${BACKUP_PATH:-/backups}/licensehub_${stamp}.dump"; PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$file"; sha256sum "$file" > "$file.sha256"; find "${BACKUP_PATH:-/backups}" -name 'licensehub_*.dump*' -mtime +"${BACKUP_RETENTION_DAYS:-14}" -delete; echo "backup completed: $file"; }
[ "${1:-}" = once ] && { run_backup; exit; }
next=0
while :; do
 now=$(date +%s)
 if [ -f "${BACKUP_PATH:-/backups}/.backup-request" ] || [ "$now" -ge "$next" ]; then
  rm -f "${BACKUP_PATH:-/backups}/.backup-request"
  run_backup
  next=$((now + ${BACKUP_INTERVAL_SECONDS:-86400}))
 fi
 sleep 10
done
