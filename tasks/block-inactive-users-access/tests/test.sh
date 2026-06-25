#!/bin/bash

mkdir -p /logs/verifier

# ── 1. Ensure PostgreSQL is running ──────────────────────────────────────
if ! pg_isready -U postgres -q > /dev/null 2>&1; then
    pg_ctlcluster 15 main start 2>/dev/null || true
    for i in $(seq 1 30); do
        pg_isready -U postgres -q > /dev/null 2>&1 && break
        sleep 1
    done
fi

if ! pg_isready -U postgres -q > /dev/null 2>&1; then
    echo "[test.sh] PostgreSQL failed to start — tests will likely fail"
fi

# ── 2. Seed the roles via SQL (idempotent) ────────────────────────────────
echo "[test.sh] Seeding roles..."
PGPASSWORD=terminus_pg_pass psql -h localhost -U postgres -d appdb << 'SQL'
INSERT INTO "Role" (name) VALUES ('USER')  ON CONFLICT (name) DO NOTHING;
INSERT INTO "Role" (name) VALUES ('ADMIN') ON CONFLICT (name) DO NOTHING;
SQL
if [ $? -ne 0 ]; then
    echo "[test.sh] Role seeding failed — tests will likely fail"
fi

# ── 3. Rebuild the TypeScript source (picks up any agent changes) ─────────
echo "[test.sh] Building TypeScript..."
cd /app
if ! npm run build 2>&1; then
    echo "[test.sh] Build failed — tests will likely fail"
fi

# ── 4. Restart the app with the fresh build ───────────────────────────────
echo "[test.sh] Starting the app..."
pkill -f "dist/server.js" 2>/dev/null || true
sleep 2
NODE_ENV=test nohup node /app/dist/server.js > /tmp/api.log 2>&1 &

# Wait up to 45 s for the server to accept connections
echo "Waiting for API to start..."
API_READY=0
for i in $(seq 1 45); do
    HTTP_CODE=$(python3 -c "
import urllib.request, urllib.error, json, sys
try:
    req = urllib.request.Request(
        'http://localhost:3000/auth/login',
        data=json.dumps({'email':'probe@test','password':'x'}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    urllib.request.urlopen(req)
    print('200')
except urllib.error.HTTPError as e:
    print(e.code)
except Exception:
    print('000')
" 2>/dev/null)
    if [ -n "$HTTP_CODE" ] && [ "$HTTP_CODE" != "000" ]; then
        echo "API is ready (HTTP $HTTP_CODE)"
        API_READY=1
        break
    fi
    sleep 1
done

if [ "$API_READY" -eq 0 ]; then
    echo "[test.sh] App did not start within 45 seconds — tests will likely fail"
    cat /tmp/api.log || true
fi

# ── 5. Run pytest verifier tests ─────────────────────────────────────────
python3 -m pytest \
    --tb=short \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

