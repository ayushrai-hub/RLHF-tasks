We need the first Clinicflow checkpoint working in `/app/clinicflow`. Implement `python -m clinicflow normalize` so it reads appointment requests from `/app/data/appointments.csv`, applies `/app/data/service_rules.json`, and writes `/app/output/m1_clean.json` by default. It must also accept `--input`, `--rules`, and `--output`; missing output parents are created and repeated runs replace the file.

Keep `/app/data/appointments.csv` and `/app/data/service_rules.json` as input fixtures. Do not edit them during normal command execution. The clean report has accepted/rejected rows plus metadata for canonical aliases, validation issues, triage scores, risk tiers, patient hold codes, accepted/rejected counts, and deterministic ordering.

The exact schema, validation order, issue labels, scoring/risk rules, line-number convention, sorting, and CLI behavior are in `/app/docs/clinicflow_contract.md` under "Milestone 1: normalize".
