#!/bin/bash
set -uo pipefail

mkdir -p /app/src /app/output /app/output/predictions

# Copy triage worker code
cp /solution/TriageWorker.kt /app/src/TriageWorker.kt

# Compile Kotlin program
kotlinc -cp /usr/share/java/gson.jar /app/src/TriageWorker.kt -include-runtime -d /app/TriageWorker.jar

# Run the compiled jar
java -cp /usr/share/java/gson.jar:/app/TriageWorker.jar TriageWorkerKt
