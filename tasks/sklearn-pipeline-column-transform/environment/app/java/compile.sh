#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
LIB="$ROOT/lib/gson-2.11.0.jar"
OUT="$ROOT/build/classes"
mkdir -p "$OUT" "$ROOT/build/libs"
find src/main/java -name '*.java' > "$ROOT/build/sources.txt"
javac -encoding UTF-8 -cp "$LIB" -d "$OUT" @"$ROOT/build/sources.txt"
jar cfm "$ROOT/build/libs/skct-pipeline-1.0.0.jar" "$ROOT/MANIFEST.MF" -C "$OUT" .
STAGE="$ROOT/build/fat_stage"
rm -rf "$STAGE" && mkdir -p "$STAGE"
( cd "$STAGE" && jar xf "$LIB" && jar xf "$ROOT/build/libs/skct-pipeline-1.0.0.jar" )
jar cfm "$ROOT/build/libs/skct-pipeline-1.0.0.jar" "$ROOT/MANIFEST.MF" -C "$STAGE" .
