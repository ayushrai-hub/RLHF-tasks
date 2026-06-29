#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RUBYLIB="${ROOT}/cmd:${ROOT}/r7_lane:${ROOT}/n4_cache:${ROOT}/v8_scope:${ROOT}/q3_trace"
mkdir -p "${ROOT}/bin" "${ROOT}/var/state" "${ROOT}/var/trace" "${ROOT}/var/anchor"

cat > "${ROOT}/bin/var_check" <<'WRAP'
#!/usr/bin/env bash
exec ruby /app/environment/cmd/var_check/main.rb "$@"
WRAP
cat > "${ROOT}/bin/var_daemon" <<'WRAP'
#!/usr/bin/env bash
exec ruby /app/environment/cmd/var_daemon/main.rb "$@"
WRAP
chmod +x "${ROOT}/bin/var_check" "${ROOT}/bin/var_daemon"

ruby "${ROOT}/scripts/gen_fixtures.rb"

echo "build_all: ok"
