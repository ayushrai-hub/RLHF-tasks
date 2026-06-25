#!/bin/bash
set -e

# Start PostgreSQL
pg_ctlcluster 15 main start 2>/dev/null || true

# Wait until PostgreSQL accepts connections
for i in $(seq 1 30); do
    if pg_isready -U postgres -q > /dev/null 2>&1; then
        echo "PostgreSQL is ready"
        break
    fi
    sleep 1
done

# Start the app in the background (bash stays as PID 1).
NODE_ENV=development node /app/dist/server.js &

# Keep the container alive.
trap 'pkill -f "dist/server.js" 2>/dev/null; exit 0' SIGTERM INT
tail -f /dev/null
