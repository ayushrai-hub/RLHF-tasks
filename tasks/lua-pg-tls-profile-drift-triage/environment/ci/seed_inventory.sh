#!/usr/bin/env bash
set -euo pipefail
ENV_ROOT="/app/environment"
bash "${ENV_ROOT}/ci/start_pg.sh"
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -c "SELECT 1 FROM pg_database WHERE datname = 'payments_tls'" | grep -q 1 \
  || runuser -u postgres -- createdb payments_tls
runuser -u postgres -- dropdb --if-exists payments_tls
runuser -u postgres -- createdb payments_tls
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -d payments_tls -f "${ENV_ROOT}/sql/schema.sql"
runuser -u postgres -- psql -v ON_ERROR_STOP=1 -d payments_tls -f "${ENV_ROOT}/sql/seed_inventory.sql"
