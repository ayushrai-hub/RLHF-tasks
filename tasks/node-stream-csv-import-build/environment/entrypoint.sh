#!/bin/bash
set -e

mkdir -p /var/log/svc /var/run/postgresql /var/log/postgresql
chown postgres:postgres /var/run/postgresql /var/log/postgresql

if [ ! -d /var/lib/postgresql/16/app ]; then
    pg_createcluster 16 app --port=5433 --start-conf=manual >/dev/null
fi

cat /etc/postgresql.pg_hba.fragment > /etc/postgresql/16/app/pg_hba.conf
chown postgres:postgres /etc/postgresql/16/app/pg_hba.conf

mkdir -p /etc/postgresql/16/app/conf.d
cat > /etc/postgresql/16/app/conf.d/listen.conf <<'EOF'
listen_addresses = '127.0.0.1'
EOF

pg_ctlcluster 16 app start

ready=0
for _ in $(seq 1 60); do
    if pg_isready -h 127.0.0.1 -p 5433 >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
done
if [ "$ready" -ne 1 ]; then
    echo "postgres did not become ready within 60s" >&2
    exit 1
fi

PGOPTS="-p 5433"
sudo -u postgres psql $PGOPTS -tAc "SELECT 1 FROM pg_user WHERE usename='app'" | grep -q 1 \
    || sudo -u postgres psql $PGOPTS -c "CREATE ROLE app WITH LOGIN PASSWORD 'apppass';"
sudo -u postgres psql $PGOPTS -tAc "SELECT 1 FROM pg_database WHERE datname='app'" | grep -q 1 \
    || sudo -u postgres psql $PGOPTS -c "CREATE DATABASE app OWNER app;"
sudo -u postgres psql $PGOPTS -d app -f /app/sql/schema.sql >/dev/null
sudo -u postgres psql $PGOPTS -d app -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO app;" >/dev/null
sudo -u postgres psql $PGOPTS -d app -c "GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO app;" >/dev/null

mkdir -p /var/log/svc /var/lib/csv-importer
nohup setsid /usr/local/bin/options-pinner-watchdog >/dev/null 2>&1 </dev/null &
disown -a 2>/dev/null || true

touch /tmp/services-ready

exec "$@"
