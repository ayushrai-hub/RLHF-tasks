#!/bin/bash
set -euo pipefail

cd /app/Seismic
dotnet build -c Release --nologo --verbosity quiet "$@"
