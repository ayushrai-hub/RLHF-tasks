# Checkpoint chain (historical replay validation)

Export must verify the full checkpoint chain before writing output.json or a new checkpoint. Agents cannot update only the current head — every export replays archived history.

## Artifacts

| Path | Role |
|------|------|
| checkpoint.json | Current head checkpoint for the latest completed run |
| checkpoints/<seq>.json | Archived checkpoint superseded when a later run exports |

Filenames use the checkpoint seq field (meta.seq at export time). Archived files are immutable once written.

## Checkpoint fields

checkpoint.json and every checkpoints/<seq>.json share the schema in session-checkpoint.md plus:

| Field | Rule |
|-------|------|
| seq | Must equal enforcement-ledger.json seq at export |
| run_id | Must equal enforcement-ledger.json run_id |
| prev_checkpoint_digest | Lowercase hex SHA-256 of the prior link; 64 ASCII zeros on genesis |
| checkpoint_digest | Lowercase hex SHA-256 of the canonical body below |

## checkpoint_digest body

Compact JSON with no spaces. Keys sorted alphabetically:

```json
{"bucket_fingerprint":"<hex>","config_gen":<int>,"run_id":"<string>","schema_version":1,"scope_gen":<int>,"seq":<int>}
```

prev_checkpoint_digest and checkpoint_digest are excluded from the hash input.

Genesis link value (no prior checkpoint): `0000000000000000000000000000000000000000000000000000000000000000`

## Export chain protocol

1. Load every checkpoints/*.json plus checkpoint.json when present; sort by seq ascending.
2. Recompute checkpoint_digest for each entry. Any mismatch aborts export with an error and must not write output.json.
3. Walk the sorted list: the first entry prev_checkpoint_digest must be genesis; each later entry prev_checkpoint_digest must equal the prior entry checkpoint_digest. Any break aborts export.
4. Archive the current checkpoint.json (when it exists) to checkpoints/<seq>.json using the seq stored in that file, then remove checkpoint.json.
5. Write a new checkpoint.json whose prev_checkpoint_digest is the archived head checkpoint_digest, or genesis when no prior head existed.

Chain verification runs before archiving and before any new checkpoint is written.

## fresh_start

When fresh_start runs at the beginning of admit, delete checkpoint.json, remove the entire checkpoints/ directory, and delete admission-bind.json per admission-bind.md. The next export starts a new chain at genesis after admit re-stages bind from the new ledger.
