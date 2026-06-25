# Trace bundle desk

Offline audit desk for Markdown debugging bundles captured during diffusion Monte Carlo campaigns. Sources live under `docs/q3_bundles/`. Policy limits sit in `policy/workflow_policy.toml`.

Build: `bash /app/scripts/build_all.sh`

Probes: `bash /app/scripts/milestone_probes.sh index|audit|clean|verify`

Contracts: `docs/index_contract.md`, `docs/strace_contract.md`, `docs/lsof_contract.md`, `docs/audit_contract.md`, `docs/cleanup_contract.md`, `docs/verification_contract.md`, `docs/troubleshooting.md`
