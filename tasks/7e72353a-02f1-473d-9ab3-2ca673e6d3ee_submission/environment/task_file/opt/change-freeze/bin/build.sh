#!/bin/bash
set -euo pipefail

/opt/change-freeze/bin/sync_vendor.sh
mkdir -p /opt/change-freeze/build
cd /opt/change-freeze/app
go build -o /opt/change-freeze/build/change-freeze .
