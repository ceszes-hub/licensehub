#!/bin/bash
set -Eeuo pipefail
trap 'echo "Installation failed at line $LINENO" >&2' ERR
command -v docker >/dev/null || { echo 'Docker Engine is required (Ubuntu 24.04 supported).'; exit 1; }
docker compose version >/dev/null
command -v openssl >/dev/null || { echo 'openssl is required'; exit 1; }
[[ -f .env ]] || cp .env.example .env
set_secret(){ key="$1"; value="$2"; grep -q "^${key}=.$" .env || sed -i "s|^${key}=$|${key}=${value}|" .env; }
set_secret DJANGO_SECRET_KEY "$(openssl rand -hex 32)"; set_secret POSTGRES_PASSWORD "$(openssl rand -hex 24)"; set_secret REDIS_PASSWORD "$(openssl rand -hex 24)"
server_name=$(sed -n 's/^TLS_SERVER_NAME=//p' .env); server_name=${server_name:-localhost}; mkdir -p docker/nginx/certs
if [[ ! -s docker/nginx/certs/fullchain.pem || ! -s docker/nginx/certs/privkey.pem ]]; then openssl req -x509 -newkey rsa:3072 -sha256 -days 365 -nodes -keyout docker/nginx/certs/privkey.pem -out docker/nginx/certs/fullchain.pem -subj "/CN=$server_name" -addext "subjectAltName=DNS:$server_name" >/dev/null 2>&1; fi
docker compose up -d --build
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py collectstatic --noinput
curl --retry 20 --retry-delay 3 -fk "https://$server_name/health/" >/dev/null
printf 'LicenseHub Enterprise installation completed.

Open:
https://%s/setup/
' "$server_name"
