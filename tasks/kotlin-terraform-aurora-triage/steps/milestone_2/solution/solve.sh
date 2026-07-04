#!/bin/bash
set -uo pipefail

mkdir -p /app/src /app/output /app/models

# Copy trainer code
cp /solution/ClassifierTrainer.kt /app/src/ClassifierTrainer.kt

# Compile Kotlin program
kotlinc -cp /usr/share/java/gson.jar /app/src/ClassifierTrainer.kt -include-runtime -d /app/ClassifierTrainer.jar

# Run the compiled jar to train the model
java -cp /usr/share/java/gson.jar:/app/ClassifierTrainer.jar ClassifierTrainerKt
