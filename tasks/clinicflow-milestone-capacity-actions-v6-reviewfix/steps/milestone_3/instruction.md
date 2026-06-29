Finish Clinicflow with `python -m clinicflow actions`. It reads `/app/output/m2_plan.json`, applies `/app/data/service_rules.json`, and writes `/app/output/m3_actions.json` by default. It must also accept `--plan`, `--rules`, and `--output`; missing output parents are created and repeated runs replace the file.

Keep both earlier commands working with their previous flags. The actions packet has action rows, grouped alerts, and metadata for scheduled/overflow action selection, urgent-risk escalation, manual-hold reason codes, owner/channel overrides, reason action overrides, alert grouping, owner/action/severity counts, malformed plan fallback, and deterministic ordering.

The exact schema, channel fallback rules, alert generation rules, reason override behavior, and cumulative workflow requirements are in `/app/docs/clinicflow_contract.md` under "Milestone 3: actions".
