require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log_error "missing required command: $1"
        return 1
    fi
}

ensure_dir() {
    local d="$1"
    if [ ! -d "$d" ]; then
        mkdir -p "$d"
    fi
}
