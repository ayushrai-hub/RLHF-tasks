The service gating stage is inconsistent under replay. Run `/app/environment/tools/run_pipeline.sh --stage m3` and repair source under `/app/environment` so `/app/output/m3_services.json` is deterministic.

The JSON must include `stage`, `restart_plan`, `gated_units`, and `blocked_units`. `restart_plan` must list only units that are restart-eligible and ready—the same unit names as `gated_units` in the same order. Do not place blocked units in `restart_plan`. Readiness token rules and harness literals are in `/app/environment/docs/contracts.md` and `/app/environment/docs/restart_rules.md`.

Fix the implementation so outputs are regenerated from live inputs. Signal completion before advancing to the next part.
