#!/bin/sh
set -eu
curl -fk https://${TLS_SERVER_NAME:-localhost}/health/
