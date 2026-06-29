Extend Clinicflow with `python -m clinicflow plan`. It reads `/app/output/m1_clean.json`, applies `/app/data/service_rules.json`, and writes `/app/output/m2_plan.json` by default. It must also accept `--clean`, `--rules`, and `--output`; missing output parents are created and repeated runs replace the file.

Do not break `python -m clinicflow normalize` or its earlier flags. The plan report has scheduled/overflow rows plus metadata for charged durations, risk-tier buffers, manual holds, site capacity/reserves, owner capacity caps, blocked site-service pairs, owner counts, capacity_used, owner_capacity_used, fallback handling, and deterministic ordering.

The exact schema, capacity gates, overflow reason order, fallback behavior, and cumulative dependency requirements are in `/app/docs/clinicflow_contract.md` under "Milestone 2: plan".
