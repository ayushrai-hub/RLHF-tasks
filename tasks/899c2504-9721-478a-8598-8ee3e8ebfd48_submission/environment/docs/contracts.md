# Pipeline contracts

- Reset workspace with `/app/environment/scripts/reset_workspace.sh` before bundled stage runs when using `run_pipeline.sh`.
- Stage entrypoint: `/app/environment/tools/run_pipeline.sh --stage m1|m2|m3|m4`.
- `pipeline.cli` also accepts `--stage`, `--base`, `--output`, and `--state` for alternate data roots with the same schemas.
- Bundled inputs under `/app/environment/config/` and `/app/environment/data/` may store the literal two-character sequence `\n` between logical lines; loaders must normalize that encoding before parsing CSV or TOML.

## Bundled outputs

`/app/output/m1_plan.json` includes `stage`, `targets`, `target_count`, `rotation_epoch`, and `actions`. `rotation_epoch` matches `/app/environment/config/state_rules.toml`. `targets` follow row order in `/app/environment/data/files.csv`. `actions` are unique non-empty lines from `/app/environment/data/rotation_actions.txt` in first-seen order.

`/app/output/m2_permissions.json` includes `stage`, `ownership_state`, `mode_state`, `drift`, and `drift_details`. `ownership_state` maps each path to `owner`, `group`, and `mode`. `drift` lists paths that mismatch the profile from ownership and mode rules. Each `drift_details` entry has `path`, `observed`, `expected`, and `mismatch_fields` (owner, group, mode order).

`/app/output/m3_services.json` includes `stage`, `restart_plan`, `gated_units`, and `blocked_units`. Required units follow `/app/environment/config/service_rules.toml` order. Units must appear in `/app/environment/data/units_allowlist.txt`. Readiness tokens `yes`, `true`, `ready`, `1`, and `y` count as yes after trim and lowercasing. `restart_plan` lists only units that are both restart-eligible and ready (the same unit names as `gated_units`, in the same order). `blocked_units` lists units that need restart but are not ready. Do not append blocked units to `restart_plan`.

`/app/output/m4_audit.json` includes `stage`, `idempotent`, `digest`, and `summary`. Summary counts are `blocked`, `drift`, and `gated`. The `digest` is a 64-character lowercase hex sha256 digest over UTF-8 bytes of newline-joined `key:value` pairs with keys sorted lexicographically (for example `blocked:1`, `drift:2`, `gated:1`). `idempotent` is false when drift or blocked lists are non-empty.

## Verifier harness literals

Pytest copies `config/` and `data/` into a temporary `--base` tree, mutates inputs, and calls `pipeline.cli` directly. Wrapper-only hardcoding of bundled JSON cannot satisfy these cases:

- **Harness epoch:** `rotation_epoch = "TB3-HARNESS-77"` in alternate `state_rules.toml`.
- **Harness action dedupe:** `rotation_actions.txt` with repeated `chmod` lines must emit `["chown", "chmod", "restart"]`.
- **Harness literal newlines:** `rotation_actions.txt` stored with the two-character `\n` between rows must still parse to three actions.
- **Harness targets:** alternate `files.csv` with a single row must emit that path alone in `targets`.
- **Harness drift:** alternate `files.csv` where only `/opt/app/b.log` drifts after fixing `/opt/app/c.log` mode to `0640`.
- **Harness restart:** alternate `services.csv` with tokens `true` and `ready` must gate both `rotate-api` and `rotate-sync` in `service_rules.toml` order; `restart_plan` must equal `gated_units`.
