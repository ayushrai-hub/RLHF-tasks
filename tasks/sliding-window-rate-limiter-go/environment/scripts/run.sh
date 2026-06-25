#!/bin/bash
cd /app && go build -o bin/rate-limiter ./cmd/limiter
/app/bin/rate-limiter analyze --traffic /app/data/traffic --output /app/output --format both
