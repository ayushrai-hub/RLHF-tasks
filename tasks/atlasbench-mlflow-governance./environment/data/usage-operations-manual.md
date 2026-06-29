# AtlasBench Usage and Operations Manual

Document ID: ATLAS-OPS-2024-REV3
Workspace scope: atlas-west offline model lab

This manual describes routine operation of the offline config hardening workflow. Policy semantics remain authoritative in `/app/data/governance-dossier.md`.

## Standard hardening run

Build the repair tool from `/app/atlas-harden`, then invoke it with the dossier, input config directory, output directory, and evidence database path. On success the tool exits 0 and writes hardened configs under `/app/output/configs/` plus SQLite evidence at `/app/output/evidence.db`.

Input configs under `/app/data/configs/` are read-only for operators. Never edit them in place; always write hardened results to `/app/output/configs/`.

## Expected artifacts

After a successful run you should see:

- Hardened YAML/TOML files in `/app/output/configs/` with the same basenames as the inputs
- `/app/output/evidence.db` containing `policy_actions` and a single `run_summary` row

Inspect `run_summary` digests when validating reproducibility across repeated runs on unchanged inputs.

## Operational checks

When offline verification fails, collect stderr from the hardening command, the `run_summary` row, and a sample of `policy_actions` rows. Compare observed outputs against the normative tables in `governance-dossier.md` (Base Policy Rules, Active Policy Exceptions, Credential Reference Map, Evidence Database Contract). Narrative appendices provide audit context only and do not grant exceptions.

| Observation | Suggested follow-up |
| ----------- | ------------------- |
| Non-zero exit before outputs are written | Confirm all four CLI paths exist and dossier tables are well formed |
| Digest fields in `run_summary` rejected by downstream checks | Re-read the Evidence Database Contract digest rules in the dossier |
| Policy outcome differs from an exception row you expected | Re-check Exception Precedence and confirm only `active=yes` rows apply |
| Tracking URI still appears credential-bearing in output | Compare hardened tracking output with the Credential Reference Map |
| Retention class absent or unexpected on an experiment | Confirm workspace defaults and per-experiment retention override flags |

Escalate unresolved policy interpretation to the governance committee. Do not patch configs under `/app/data/configs/` directly.
