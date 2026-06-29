#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
JAVA_HOME="${JAVA_HOME:-$(dirname "$(dirname "$(readlink -f "$(command -v javac)")")")}"
INC="$JAVA_HOME/include"
INC_L="$INC/linux"
g++ -shared -fPIC -I"$INC" -I"$INC_L" -o libskct_kernel.so skct_kernel.cpp
