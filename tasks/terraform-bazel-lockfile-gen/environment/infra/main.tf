terraform {
  required_version = ">= 1.5.0"
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "3.2.2"
    }
  }
}

resource "null_resource" "emit" {
  triggers = {
    entry = var.root_entry
  }
  provisioner "local-exec" {
    command = "ROOT_ENTRY=${var.root_entry} DEPOT_URL=http://127.0.0.1:8787/catalog /app/environment/bin/pipeline"
  }
}
