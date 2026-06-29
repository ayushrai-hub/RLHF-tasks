#!/usr/bin/env bash
set -euo pipefail

export PATH="/usr/local/cargo/bin:/usr/local/bin:/usr/bin:${PATH:-}"
export CARGO_TERM_COLOR=never
export CARGO_BUILD_JOBS=2

cd /app

CARGO="/usr/local/cargo/bin/cargo"
SCCACHE="/usr/local/bin/sccache"
MINIO_PID_FILE="/var/run/minio/minio.pid"
MINIO_LOG="/var/run/minio/minio.log"
PHASE_DIR="/tmp/sccache-phases"
BUILD_TIMEOUT_SEC=900

read_toml_value() {
    local file=$1
    local key=$2
    grep -E "^${key}[[:space:]]*=" "$file" | head -1 | sed -E 's/^[^=]*=[[:space:]]*//; s/^"//; s/"$//; s/[[:space:]]+$//'
}

load_backend_config() {
    local minio_cfg="/app/config/backend-cache.toml"
    local signing_cfg="/app/config/backend-signing.keys"

    if [ ! -f "$minio_cfg" ]; then
        echo "missing production config: $minio_cfg" >&2
        exit 1
    fi
    if [ ! -f "$signing_cfg" ]; then
        echo "missing signing config: $signing_cfg" >&2
        exit 1
    fi

    SCCACHE_ENDPOINT="$(read_toml_value "$minio_cfg" endpoint)"
    SCCACHE_BUCKET="$(read_toml_value "$minio_cfg" bucket)"
    SCCACHE_REGION="$(read_toml_value "$minio_cfg" region)"
    MINIO_DATA_DIR="$(read_toml_value "$minio_cfg" data_dir)"
    MINIO_API_PORT="$(read_toml_value "$minio_cfg" api_port)"

    local tls_value path_style_value
    tls_value="$(read_toml_value "$minio_cfg" tls)"
    if [ "$tls_value" = "true" ]; then
        SCCACHE_S3_USE_SSL=true
    else
        SCCACHE_S3_USE_SSL=false
    fi

    path_style_value="$(read_toml_value "$minio_cfg" path_style)"
    if [ "$path_style_value" = "true" ]; then
        SCCACHE_S3_USE_PATH_STYLE=true
    else
        SCCACHE_S3_USE_PATH_STYLE=false
    fi

    MERIDIAN_S3_ACCESS_KEY=""
    MERIDIAN_S3_SECRET_KEY=""
    # shellcheck disable=SC1090
    source "$signing_cfg"

    if [ -z "${MERIDIAN_S3_ACCESS_KEY:-}" ] || [ -z "${MERIDIAN_S3_SECRET_KEY:-}" ]; then
        echo "backend-signing.keys must define MERIDIAN_S3_ACCESS_KEY and MERIDIAN_S3_SECRET_KEY" >&2
        exit 1
    fi

    export SCCACHE_ENDPOINT SCCACHE_BUCKET SCCACHE_REGION SCCACHE_S3_USE_SSL
    export SCCACHE_S3_USE_PATH_STYLE
    export MINIO_DATA_DIR MINIO_API_PORT
    export AWS_ACCESS_KEY_ID="$MERIDIAN_S3_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$MERIDIAN_S3_SECRET_KEY"
    export AWS_EC2_METADATA_DISABLED=true
    export AWS_METADATA_DISABLED=true
    export RUSTC_WRAPPER=sccache
    export SCCACHE_DIR=/var/cache/sccache-meridian
}

minio_ready() {
    mc alias set local "http://127.0.0.1:${MINIO_API_PORT}" minioadmin minioadmin >/dev/null 2>&1
}

stop_minio() {
    if [ -f "$MINIO_PID_FILE" ]; then
        kill "$(cat "$MINIO_PID_FILE")" 2>/dev/null || true
        rm -f "$MINIO_PID_FILE"
    fi
    pkill -f 'minio server' 2>/dev/null || true
}

start_minio() {
    stop_minio
    mkdir -p "$MINIO_DATA_DIR" /var/run/minio "$PHASE_DIR" /app/reports
    MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin \
        minio server "$MINIO_DATA_DIR" --address ":${MINIO_API_PORT}" --console-address ":9001" \
        >"$MINIO_LOG" 2>&1 &
    echo $! >"$MINIO_PID_FILE"
    for _ in $(seq 1 60); do
        if minio_ready && mc mb --ignore-existing "local/${SCCACHE_BUCKET}" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    echo "minio failed to start" >&2
    cat "$MINIO_LOG" >&2 || true
    exit 1
}

configure_sccache() {
    export CARGO_INCREMENTAL=0
    mkdir -p /app/.cargo
    cat > /app/.cargo/config.toml <<'EOF'
[build]
jobs = 2
rustc-wrapper = "sccache"

[term]
color = "never"
EOF
}

export_sccache_env() {
    export SCCACHE_ENDPOINT SCCACHE_BUCKET SCCACHE_REGION SCCACHE_S3_USE_SSL
    export SCCACHE_S3_USE_PATH_STYLE
    export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
    export AWS_EC2_METADATA_DISABLED=true
    export AWS_METADATA_DISABLED=true
    export RUSTC_WRAPPER=sccache
    export SCCACHE_DIR=/var/cache/sccache-meridian
    export CARGO_INCREMENTAL=0
}

sccache_using_s3() {
    local stats
    stats=$("$SCCACHE" --show-stats 2>/dev/null || true)
    printf '%s\n' "$stats" | grep -qi 's3'
}

restart_sccache_server() {
    export_sccache_env
    minio_ready || start_minio
    "$SCCACHE" --stop-server >/dev/null 2>&1 || true
    "$SCCACHE" --start-server >/dev/null 2>&1
    if ! sccache_using_s3; then
        sleep 1
        "$SCCACHE" --stop-server >/dev/null 2>&1 || true
        "$SCCACHE" --start-server >/dev/null 2>&1
    fi
    if ! sccache_using_s3; then
        echo "sccache server is not using the configured S3 backend" >&2
        "$SCCACHE" --show-stats >&2 || true
        exit 1
    fi
    "$SCCACHE" --zero-stats >/dev/null 2>&1 || true
}

wait_for_remote_cache() {
    minio_ready
    local attempt object_count
    for attempt in $(seq 1 30); do
        object_count=$(mc ls --recursive "local/${SCCACHE_BUCKET}/" 2>/dev/null | wc -l | tr -d ' ')
        if [ "${object_count:-0}" -gt 0 ]; then
            return 0
        fi
        sleep 1
    done
    echo "remote cache bucket ${SCCACHE_BUCKET} has no objects after cold build" >&2
    exit 1
}

read_stats() {
    local stats hits misses compilations
    stats=$("$SCCACHE" --show-stats)
    hits=$(printf '%s\n' "$stats" | awk '/^Cache hits[[:space:]]/ { print $NF; exit }')
    misses=$(printf '%s\n' "$stats" | awk '/^Cache misses[[:space:]]/ { print $NF; exit }')
    compilations=$(printf '%s\n' "$stats" | awk '/^Non-cacheable compilations[[:space:]]/ { print $NF; exit }')
    printf '%s %s %s' "${hits:-0}" "${misses:-0}" "${compilations:-0}"
}

phase_seconds() {
    local start=$1
    local end=$2
    python3 - <<PY
start = float("$start")
end = float("$end")
seconds = end - start
if seconds < 0.001:
    seconds = 0.001
print(round(seconds, 6))
PY
}

run_workspace_build() {
    timeout "$BUILD_TIMEOUT_SEC" "$CARGO" build --workspace --locked
}

time_build() {
    local label=$1
    restart_sccache_server
    local start end hits misses compilations elapsed
    start=$(date +%s.%N)
    run_workspace_build
    end=$(date +%s.%N)
    sleep 2
    read -r hits misses compilations <<< "$(read_stats)"
    elapsed=$(phase_seconds "$start" "$end")
    python3 - <<PY
import json
from pathlib import Path

payload = {
    "seconds": float("$elapsed"),
    "hits": int("$hits"),
    "misses": int("$misses"),
    "compilations": int("$compilations"),
}
Path("$PHASE_DIR").mkdir(parents=True, exist_ok=True)
Path("$PHASE_DIR/${label}.json").write_text(json.dumps(payload) + "\n")
PY
}

clean_targets() {
    find /app -type d -name target -prune -exec rm -rf {} +
}

clear_remote_bucket() {
    minio_ready
    mc rm --recursive --force "local/${SCCACHE_BUCKET}" >/dev/null 2>&1 || true
    mc mb --ignore-existing "local/${SCCACHE_BUCKET}" >/dev/null 2>&1
    restart_sccache_server
}

write_report() {
    python3 - <<'PY'
import json
import sys
from pathlib import Path

phase_dir = Path("/tmp/sccache-phases")
cold = json.loads((phase_dir / "cold.json").read_text())
warm = json.loads((phase_dir / "warm.json").read_text())
post = json.loads((phase_dir / "post_clean.json").read_text())

errors = []
if warm["seconds"] >= cold["seconds"] * 0.5:
    errors.append(
        f"warm_seconds ({warm['seconds']}) must be less than half of cold_seconds ({cold['seconds']})"
    )
if cold["seconds"] < 5.0:
    errors.append(
        f"cold_seconds ({cold['seconds']}) must reflect a multi-crate compile of several seconds"
    )
if warm["misses"] != 0 or warm["compilations"] != 0:
    errors.append(
        "warm phase must record zero misses and compilations "
        f"(misses={warm['misses']}, compilations={warm['compilations']})"
    )
if cold["misses"] <= 0:
    errors.append("cold phase must record cache misses")
if cold["hits"] != 0:
    errors.append("cold phase must record zero prior cache hits")
if post["hits"] <= 0:
    errors.append("post_clean phase must record cache hits")
if post["hits"] <= post["compilations"]:
    errors.append("post_clean hits must dominate compilations")
if post["hits"] < cold["misses"]:
    errors.append("post_clean hits must be at least cold misses")
if post["seconds"] < 1.0:
    errors.append("post_clean_seconds must reflect a rebuild after deleting target/")
if post["seconds"] <= warm["seconds"]:
    errors.append("post_clean_seconds must exceed warm_seconds")

if errors:
    for err in errors:
        print(err, file=sys.stderr)
    sys.exit(1)

report = {
    "cold_seconds": cold["seconds"],
    "warm_seconds": warm["seconds"],
    "post_clean_seconds": post["seconds"],
    "cold": {
        "hits": cold["hits"],
        "misses": cold["misses"],
        "compilations": cold["compilations"],
    },
    "warm": {
        "hits": warm["hits"],
        "misses": warm["misses"],
        "compilations": warm["compilations"],
    },
    "post_clean": {
        "hits": post["hits"],
        "misses": post["misses"],
        "compilations": post["compilations"],
    },
}

Path("/app/reports").mkdir(parents=True, exist_ok=True)
Path("/app/reports/sccache-benchmark.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
PY
}

capture_replay_verification() {
    clean_targets
    restart_sccache_server
    run_workspace_build
    sleep 2
    "$SCCACHE" --show-stats > /app/reports/sccache-replay-stats.txt
    read -r replay_hits replay_misses _ <<< "$(read_stats)"
    local cold_misses
    cold_misses=$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("/tmp/sccache-phases/cold.json").read_text())["misses"])
PY
)
    if [ "${replay_hits:-0}" -lt "$cold_misses" ]; then
        echo "replay verification recorded ${replay_hits:-0} hits; expected at least $cold_misses" >&2
        cat /app/reports/sccache-replay-stats.txt >&2 || true
        exit 1
    fi
    if [ "${replay_misses:-0}" -ne 0 ]; then
        echo "replay verification recorded ${replay_misses} misses; expected zero" >&2
        cat /app/reports/sccache-replay-stats.txt >&2 || true
        exit 1
    fi
}

load_backend_config
mkdir -p /var/cache/sccache-meridian
start_minio
configure_sccache
restart_sccache_server
mkdir -p /app/reports "$PHASE_DIR"

clear_remote_bucket
time_build cold
wait_for_remote_cache
time_build warm

if python3 - <<'PY'
import json
from pathlib import Path
cold = json.loads(Path("/tmp/sccache-phases/cold.json").read_text())
warm = json.loads(Path("/tmp/sccache-phases/warm.json").read_text())
raise SystemExit(0 if warm["seconds"] < cold["seconds"] and warm["misses"] == 0 and warm["compilations"] == 0 else 1)
PY
then
    :
else
    time_build warm
fi

clean_targets
time_build post_clean

if python3 - <<'PY'
import json
from pathlib import Path

post = json.loads(Path("/tmp/sccache-phases/post_clean.json").read_text())
raise SystemExit(0 if post["hits"] > 0 else 1)
PY
then
    :
else
    echo "post_clean recorded no cache hits; retrying once" >&2
    wait_for_remote_cache
    clean_targets
    time_build post_clean
fi

write_report
capture_replay_verification

if [ ! -f /app/target/debug/meridian-cli ]; then
    run_workspace_build
fi

if [ ! -f /app/target/debug/meridian-cli ]; then
    echo "missing /app/target/debug/meridian-cli after benchmark" >&2
    exit 1
fi

if [ ! -f /app/reports/sccache-benchmark.json ]; then
    echo "missing /app/reports/sccache-benchmark.json" >&2
    exit 1
fi
