#!/bin/bash
set +e
set +u
set +o pipefail

export PATH="/usr/local/cargo/bin:/usr/local/bin:/usr/bin:${PATH:-}"
export CARGO_TERM_COLOR=never

mkdir -p /logs/verifier /var/minio/data /var/run/minio /tmp/pytest_cache
echo 0 > /logs/verifier/reward.txt

ensure_reward_on_exit() {
    if [ ! -f /logs/verifier/reward.txt ]; then
        echo 0 > /logs/verifier/reward.txt
    fi
}

fail() {
    echo 0 > /logs/verifier/reward.txt
    exit 0
}

read_toml_value() {
    local file=$1
    local key=$2
    grep -E "^${key}[[:space:]]*=" "$file" 2>/dev/null | head -1 | sed -E 's/^[^=]*=[[:space:]]*//; s/^"//; s/"$//; s/[[:space:]]+$//'
}

load_tool_env() {
    local minio_cfg="/app/config/backend-cache.toml"
    local signing_cfg="/app/config/backend-signing.keys"

    export AWS_EC2_METADATA_DISABLED=true
    export AWS_METADATA_DISABLED=true

    if [ ! -f "$minio_cfg" ] || [ ! -f "$signing_cfg" ]; then
        echo "Warning: missing backend config; verifier tests may fail" >&2
        return 1
    fi

    SCCACHE_ENDPOINT="$(read_toml_value "$minio_cfg" endpoint)"
    SCCACHE_BUCKET="$(read_toml_value "$minio_cfg" bucket)"
    SCCACHE_REGION="$(read_toml_value "$minio_cfg" region)"
    local tls_value path_style_value
    tls_value="$(read_toml_value "$minio_cfg" tls)"
    path_style_value="$(read_toml_value "$minio_cfg" path_style)"

    MERIDIAN_S3_ACCESS_KEY=""
    MERIDIAN_S3_SECRET_KEY=""
    # shellcheck disable=SC1090
    source "$signing_cfg" 2>/dev/null || {
        echo "Warning: could not source backend-signing.keys" >&2
        return 1
    }

    if [ -z "${MERIDIAN_S3_ACCESS_KEY:-}" ] || [ -z "${MERIDIAN_S3_SECRET_KEY:-}" ]; then
        echo "Warning: backend-signing.keys missing MERIDIAN_S3_ACCESS_KEY/MERIDIAN_S3_SECRET_KEY" >&2
        return 1
    fi

    export SCCACHE_ENDPOINT SCCACHE_BUCKET SCCACHE_REGION
    if [ "$tls_value" = "true" ]; then
        export SCCACHE_S3_USE_SSL=true
    else
        export SCCACHE_S3_USE_SSL=false
    fi
    if [ "$path_style_value" = "true" ]; then
        export SCCACHE_S3_USE_PATH_STYLE=true
    else
        export SCCACHE_S3_USE_PATH_STYLE=false
    fi
    export AWS_ACCESS_KEY_ID="$MERIDIAN_S3_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$MERIDIAN_S3_SECRET_KEY"
    export RUSTC_WRAPPER=sccache
    export SCCACHE_DIR=/var/cache/sccache-meridian
    return 0
}

kill_stray_build_procs() {
    pkill -9 -f 'cargo build' 2>/dev/null || true
    pkill -9 -f 'cargo check' 2>/dev/null || true
    pkill -9 -f 'rustc ' 2>/dev/null || true
}

restart_sccache_server() {
    if ! command -v sccache >/dev/null 2>&1; then
        return 0
    fi
    sccache --stop-server >/dev/null 2>&1 || true
    sccache --start-server >/dev/null 2>&1 || true
}

ensure_sccache_responds() {
    if ! command -v sccache >/dev/null 2>&1; then
        return 0
    fi
    if timeout 5 sccache --show-stats >/dev/null 2>&1; then
        return 0
    fi
    restart_sccache_server
}

stop_minio() {
    if [ -f /var/run/minio/minio.pid ]; then
        kill "$(cat /var/run/minio/minio.pid)" 2>/dev/null || true
        rm -f /var/run/minio/minio.pid
    fi
    pkill -f 'minio server' 2>/dev/null || true
}

start_minio() {
    stop_minio
    local minio_cfg="/app/config/backend-cache.toml"
    MINIO_DATA_DIR="/var/minio/data"
    MINIO_API_PORT="9000"
    BUCKET="rust-sccache"
    if [ -f "$minio_cfg" ]; then
        MINIO_DATA_DIR="$(read_toml_value "$minio_cfg" data_dir)"
        MINIO_API_PORT="$(read_toml_value "$minio_cfg" api_port)"
        BUCKET="$(read_toml_value "$minio_cfg" bucket)"
    fi
    mkdir -p "$MINIO_DATA_DIR" /var/run/minio
    MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin \
        minio server "$MINIO_DATA_DIR" --address ":${MINIO_API_PORT}" --console-address ":9001" \
        >/var/run/minio/minio.log 2>&1 &
    echo $! >/var/run/minio/minio.pid
    for _ in $(seq 1 30); do
        if mc alias set local "http://127.0.0.1:${MINIO_API_PORT}" minioadmin minioadmin >/dev/null 2>&1; then
            mc mb --ignore-existing "local/${BUCKET}" >/dev/null 2>&1 || true
            return 0
        fi
        sleep 1
    done
    echo "Warning: MinIO failed to start for verifier" >&2
    tail -n 20 /var/run/minio/minio.log >&2 || true
    return 1
}

ensure_minio() {
    local minio_cfg="/app/config/backend-cache.toml"
    MINIO_API_PORT="9000"
    BUCKET="rust-sccache"
    if [ -f "$minio_cfg" ]; then
        MINIO_API_PORT="$(read_toml_value "$minio_cfg" api_port)"
        BUCKET="$(read_toml_value "$minio_cfg" bucket)"
    fi
    if mc alias set local "http://127.0.0.1:${MINIO_API_PORT}" minioadmin minioadmin >/dev/null 2>&1; then
        mc mb --ignore-existing "local/${BUCKET}" >/dev/null 2>&1 || true
        return 0
    fi
    start_minio
}

prepare_verifier_environment() {
    kill_stray_build_procs
    sleep 0.5
    ensure_minio || echo "Warning: MinIO unavailable; continuing with pytest" >&2
    load_tool_env || true
    ensure_sccache_responds
}

trap 'kill_stray_build_procs; ensure_reward_on_exit' EXIT
trap 'kill_stray_build_procs; echo 0 > /logs/verifier/reward.txt; exit 0' INT TERM HUP QUIT

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script." >&2
    fail
fi

if ! command -v timeout >/dev/null 2>&1; then
    echo "Error: timeout(1) is required for the verifier hard cap." >&2
    fail
fi

load_tool_env || true

kill_stray_build_procs
if [ ! -f /app/reports/sccache-benchmark.json ]; then
    restart_sccache_server
fi

if [ -f /app/reports/sccache-benchmark.json ]; then
    prepare_verifier_environment
    PYTEST_TIMEOUT=1200
    PYTEST_ARGS=(-o cache_dir=/tmp/pytest_cache --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA)
else
    echo "No benchmark report yet; running fast verifier fail path" >&2
    PYTEST_TIMEOUT=120
    PYTEST_ARGS=(-x -o cache_dir=/tmp/pytest_cache --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA)
fi

echo 0 > /logs/verifier/reward.txt

# Hard cap (below task.toml [verifier].timeout_sec) so the harness always gets reward.txt.
# Do not insert ANY command between this pytest invocation and the reward if block.
timeout --preserve-status "$PYTEST_TIMEOUT" /opt/test-venv/bin/pytest "${PYTEST_ARGS[@]}"
PYTEST_RC=$?

if [ "$PYTEST_RC" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
