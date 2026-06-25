#!/bin/bash
set -euo pipefail
cd /app
export GRADLE_USER_HOME=/app/.gradle
gradle :q7cli:jar --quiet
mkdir -p /app/build/libs
cp /app/q7cli/build/libs/trace-audit-cli-0.1.0.jar /app/build/libs/trace-audit-cli.jar
date -u +%Y%m%dT%H%M%SZ > /app/data/last_build.txt
