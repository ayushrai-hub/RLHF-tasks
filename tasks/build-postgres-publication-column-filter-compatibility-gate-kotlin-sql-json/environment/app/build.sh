#!/bin/bash
set -euo pipefail

mkdir -p /app/build
kotlinc /app/src/main/kotlin/com/terminus/pubgate/*.kt \
  -jdk-home /usr/lib/jvm/java-11-openjdk-amd64 \
  -cp /usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar \
  -d /app/build/pubgate.jar
