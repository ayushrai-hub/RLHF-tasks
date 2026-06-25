# Mission ingest rules

Normative validation and persistence for `mission-ingest`. Wire layout is in `/app/docs/mseq-format.md`; SQLite names are in `/app/docs/db-schema.md`.

## CLI identity checks

- Footer `upload_id` must equal `--upload-id`.
- Each waypoint record's embedded `upload_id` string must equal `--upload-id`.
- Footer `expected_count` must equal the number of waypoint records parsed from the log.

## Record order and duplicates

- Physical file order may differ from ascending `seq`; ingest accepts any order.
- Duplicate `seq` within the same upload aborts ingest with rollback.
- Do **not** reject uploads because `seq` is not strictly increasing in file order — only duplicate `seq` is forbidden.

## CRC and resync

- Any waypoint CRC failure on a record that begins with valid `MQ` magic aborts the entire upload (do not byte-scan past that record).
- Leading noise and non-record garbage may be skipped one byte at a time until `MQ` aligns; that resync rule does **not** apply after a waypoint header fails CRC validation.

## Transactions and idempotency

- All waypoint rows for the upload commit in one transaction after footer checks pass; failure rolls back the entire upload.
- After a successful commit for `(vehicle_id, upload_id)`, a later ingest with the same pair exits successfully without changing any stored waypoint fields (idempotent replay preserves the first committed payload).

## Failed ingest

No rows in `waypoints` or `upload_commits` for that `(vehicle_id, upload_id)` pair. Schema tables must still exist.
