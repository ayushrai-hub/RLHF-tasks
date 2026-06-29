#!/bin/bash
set -euo pipefail

db="${1:-/app/data/catalog.db}"
sqlite3 "$db" '.tables'
sqlite3 "$db" 'SELECT schema_name, table_name, replica_identity FROM tables ORDER BY schema_name, table_name;'
sqlite3 "$db" 'SELECT publication_name, schema_name, table_name, columns_json FROM publication_tables ORDER BY publication_name, schema_name, table_name;'
