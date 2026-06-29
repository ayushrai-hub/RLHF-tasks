#!/bin/sh
set -eu
cmake -S /app -B /app/build
cmake --build /app/build
