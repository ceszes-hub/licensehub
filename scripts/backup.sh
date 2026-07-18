#!/bin/sh
set -eu
docker compose exec -T backup /bin/sh /backup.sh once
