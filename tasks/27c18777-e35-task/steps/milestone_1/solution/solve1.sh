#!/bin/bash
set -euo pipefail

mkdir -p /app/src /app/output
cp /solution/ProtocolExtractor.kt /app/src/ProtocolExtractor.kt
kotlinc -cp /usr/share/java/gson.jar /app/src/ProtocolExtractor.kt -include-runtime -d /app/ProtocolExtractor.jar
java -cp /usr/share/java/gson.jar:/app/ProtocolExtractor.jar ProtocolExtractorKt
