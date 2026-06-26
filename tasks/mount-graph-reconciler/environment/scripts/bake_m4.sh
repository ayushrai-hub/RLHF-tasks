#!/bin/bash
set -euo pipefail
mkdir -p /app/bin
cat > /app/bin/mgr_run <<'EOF'
#!/bin/bash
exec tsx /app/environment/tools/mgr_cli/entry.ts "$@"
EOF
chmod +x /app/bin/mgr_run
