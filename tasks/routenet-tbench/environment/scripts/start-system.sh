#!/usr/bin/env bash
set -euo pipefail

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
PG_BIN="/usr/lib/postgresql/15/bin"
PG_USER="${PG_USER:-trainer}"
PG_PASSWORD="${PG_PASSWORD:-trainer}"
PG_DB="${PG_DB:-routenet}"
PG_PORT="${PG_PORT:-5432}"
PG_HOST="${PG_HOST:-127.0.0.1}"
SEED_MARKER="${PGDATA}/.routenet-seeded"

if [ ! -f "${PGDATA}/PG_VERSION" ]; then
    echo "initializing postgres cluster..."
    mkdir -p "${PGDATA}"
    chown -R postgres:postgres "${PGDATA}"
    sudo -u postgres "${PG_BIN}/initdb" \
        --pgdata="${PGDATA}" \
        --username=postgres \
        --auth-local=trust \
        --auth-host=trust \
        --encoding=UTF8 \
        --locale=C
    {
        echo "listen_addresses = '127.0.0.1'"
        echo "port = ${PG_PORT}"
        echo "fsync = off"
        echo "synchronous_commit = off"
    } >> "${PGDATA}/postgresql.conf"
fi

if ! sudo -u postgres "${PG_BIN}/pg_ctl" -D "${PGDATA}" status >/dev/null 2>&1; then
    echo "starting postgres..."
    sudo -u postgres "${PG_BIN}/pg_ctl" -D "${PGDATA}" -l /tmp/pg.log -w start >/dev/null
fi

deadline=$(( $(date +%s) + 30 ))
while ! sudo -u postgres "${PG_BIN}/psql" -h 127.0.0.1 -p "${PG_PORT}" -U postgres -c "SELECT 1" >/dev/null 2>&1; do
    if [ "$(date +%s)" -gt "${deadline}" ]; then
        echo "postgres superuser did not become ready within 30s" >&2
        exit 1
    fi
    sleep 0.5
done

if [ ! -f "${SEED_MARKER}" ]; then
    echo "seeding routenet database..."
    if ! sudo -u postgres "${PG_BIN}/psql" -h 127.0.0.1 -p "${PG_PORT}" -U postgres -tAc \
        "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1; then
        sudo -u postgres "${PG_BIN}/psql" -h 127.0.0.1 -p "${PG_PORT}" -U postgres -c \
            "CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASSWORD}' SUPERUSER;"
    fi
    if ! sudo -u postgres "${PG_BIN}/psql" -h 127.0.0.1 -p "${PG_PORT}" -U postgres -tAc \
        "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1; then
        sudo -u postgres "${PG_BIN}/createdb" -h 127.0.0.1 -p "${PG_PORT}" -O "${PG_USER}" "${PG_DB}"
    fi
    PGPASSWORD="${PG_PASSWORD}" node /app/scripts/load-seed.js
    touch "${SEED_MARKER}"
    chown postgres:postgres "${SEED_MARKER}"
fi

deadline=$(( $(date +%s) + 30 ))
while true; do
    if PGPASSWORD="${PG_PASSWORD}" "${PG_BIN}/psql" -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" -c "SELECT 1" >/dev/null 2>&1; then
        break
    fi
    if [ "$(date +%s)" -gt "${deadline}" ]; then
        echo "postgres did not accept trainer connections within 30s" >&2
        exit 1
    fi
    sleep 0.5
done

echo "postgres is ready on ${PG_HOST}:${PG_PORT} (db=${PG_DB}, user=${PG_USER})"
