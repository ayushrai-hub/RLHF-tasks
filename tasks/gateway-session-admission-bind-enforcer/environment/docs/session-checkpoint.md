# Session checkpoint (audit binding)

Every run writes checkpoint.json in the session directory during the export stage after state.json and meta.json are updated. The bucket_fingerprint binds live token counts from enforcement-ledger.json bucket_tokens for audit replay. Historical chain rules are in checkpoint-chain.md.

## Fields

| Field | Rule |
|-------|------|
| schema_version | Always 1 |
| seq | Must equal enforcement-ledger.json seq |
| run_id | Must equal enforcement-ledger.json run_id |
| config_gen | Must equal ledger config_gen after the run |
| scope_gen | Must equal ledger scope_gen after the run |
| bucket_fingerprint | Lowercase hex SHA-256 of compact JSON mapping each backend id (sorted alphabetically) to ledger bucket_tokens |
| prev_checkpoint_digest | Prior link per checkpoint-chain.md |
| checkpoint_digest | Self digest per checkpoint-chain.md |

The fingerprint uses live token counts, not capacity ceilings.

Milestone 1 runs still write checkpoint.json even though milestone 1 output omits state_digest validation in agent workflows; the file must stay aligned with persisted buckets for audit replay.
