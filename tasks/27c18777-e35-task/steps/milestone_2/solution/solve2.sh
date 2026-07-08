#!/bin/bash
set -euo pipefail

mkdir -p /app/src /app/output /app/models
cp /solution/ClassifierTrainer.kt /app/src/ClassifierTrainer.kt
kotlinc -cp /usr/share/java/gson.jar /app/src/ClassifierTrainer.kt -include-runtime -d /app/ClassifierTrainer.jar
java -cp /usr/share/java/gson.jar:/app/ClassifierTrainer.jar ClassifierTrainerKt
