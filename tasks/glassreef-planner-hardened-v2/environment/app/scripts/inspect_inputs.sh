#!/usr/bin/env bash
set -euo pipefail
wc -l /app/data/network/stations.csv /app/data/network/spans.csv /app/data/weather/windows.csv /app/data/currents/corridors.csv /app/data/vessels/ships.csv
