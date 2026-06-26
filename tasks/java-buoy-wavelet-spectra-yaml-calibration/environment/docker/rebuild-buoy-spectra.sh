#!/usr/bin/env bash
set -euo pipefail
mvn -q -f /app/pom.xml -DskipTests package
