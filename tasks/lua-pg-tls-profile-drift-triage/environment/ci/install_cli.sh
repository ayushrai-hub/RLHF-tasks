#!/usr/bin/env bash
set -euo pipefail
install -d /app/bin
install -m 0755 /app/environment/cli/ingressctl /app/bin/ingressctl
test -x /app/bin/ingressctl
