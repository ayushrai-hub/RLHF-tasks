#!/bin/bash
set -euo pipefail

mkdir -p /app/src /app/output /app/output/predictions
cp /solution/TriageWorker.kt /app/src/TriageWorker.kt
kotlinc -cp /usr/share/java/gson.jar /app/src/TriageWorker.kt -include-runtime -d /app/TriageWorker.jar
java -cp /usr/share/java/gson.jar:/app/TriageWorker.jar TriageWorkerKt
