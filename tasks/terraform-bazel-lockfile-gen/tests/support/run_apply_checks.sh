#!/bin/bash
set -euo pipefail
export ROOT_ENTRY="${ROOT_ENTRY:-alpha}"
bash /app/environment/scripts/start_svc.sh
rm -rf /app/output
mkdir -p /app/output
cd /app/environment/infra
terraform apply -auto-approve -var "root_entry=${ROOT_ENTRY}" -replace="null_resource.emit"
