#!/bin/bash
set -Eeuo pipefail
git pull --ff-only
docker compose build --pull
docker compose up -d
docker compose exec -T web python manage.py migrate --noinput
