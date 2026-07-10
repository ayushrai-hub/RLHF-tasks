db_init() {
    require_cmd sqlite3 || return 1
    ensure_dir "$(dirname "$DB_PATH")"
    if [ ! -f "$DB_PATH" ]; then
        sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
    fi
}

db_exec() {
    sqlite3 "$DB_PATH" "$1"
}
