#!/bin/bash
set -euo pipefail

/app/app_entrypoint.py parse \
  --schema /app/input/publisher_schema.sql \
  --publications /app/input/publications.sql \
  --subscriptions /app/input/subscriptions.json \
  --db /app/data/catalog.db \
  --out /app/out/catalog.json

/app/app_entrypoint.py validate \
  --catalog /app/out/catalog.json \
  --out /app/out/validation.json

/app/app_entrypoint.py plan \
  --validation /app/out/validation.json \
  --out /app/out/plan.json \
  --sql /app/out/plan.sql
