#!/bin/bash
# Compile the cronq sources and package them into /app/cronq.jar.
set -euo pipefail
cd /app
rm -rf build
mkdir -p build
javac -d build $(find src -name '*.java')
jar --create --file cronq.jar --main-class com.cronq.Cli -C build .
