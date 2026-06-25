#!/bin/bash
set -euo pipefail

exec dotnet /app/Seismic/bin/Release/net8.0/Seismic.dll "$@"
