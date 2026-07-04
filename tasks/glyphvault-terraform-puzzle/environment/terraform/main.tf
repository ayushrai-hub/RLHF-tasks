terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "3.2.2"
    }
  }
}

resource "null_resource" "seed_puzzle_db" {
  triggers = {
    sql_hash = filesha256("${path.module}/seed.sql")
  }

  provisioner "local-exec" {
    command = "sqlite3 ${var.db_path} < ${path.module}/seed.sql"
  }
}

output "db_path" {
  value = var.db_path
}
