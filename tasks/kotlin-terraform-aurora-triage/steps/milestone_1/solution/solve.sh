#!/bin/bash
set -uo pipefail

mkdir -p /app/src /app/output

# Copy files
cp /solution/ProtocolExtractor.kt /app/src/ProtocolExtractor.kt

# Compile Kotlin program
kotlinc -cp /usr/share/java/gson.jar /app/src/ProtocolExtractor.kt -include-runtime -d /app/ProtocolExtractor.jar

# Run the compiled jar
java -cp /usr/share/java/gson.jar:/app/ProtocolExtractor.jar ProtocolExtractorKt
