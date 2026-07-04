#!/bin/bash
set -euo pipefail
export TF_CLI_CONFIG_FILE=/app/environment/terraform/.terraformrc
PROVIDER_BIN=/app/environment/terraform/provider-mirror/registry.terraform.io/hashicorp/null/3.2.2/linux_amd64/terraform-provider-null_v3.2.2_x5
chmod +x "$PROVIDER_BIN"
terraform -chdir=/app/environment/terraform init -backend=false -input=false >/dev/null
terraform -chdir=/app/environment/terraform apply -auto-approve -input=false >/dev/null
