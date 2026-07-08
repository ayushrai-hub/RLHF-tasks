# Survey ingest contract

Traces from all six survey lanes merge into survey-ingest-catalog.json.

## Binding summary (read first)

| Rule | Requirement |
|------|-------------|
| traces array order | sort merged rows by sample_id ascending only |
| forbidden catalog sort | do not sort by recorded_at descending or by source lane |
| catalog_digest third geo field | literal UTF-8 string survey-ingest-catalog on every line (not the trace source modality) |
| catalog_digest algorithm | sha256 hex lowercase over sorted geo lines (64 hex chars, not a truncated hash) |

Example geo line for sample tr-bh-001:

```
geo|tr-bh-001|survey-ingest-catalog|copper-belt-north|1|2024-03-01T08:00:00Z|basalt-cap
```

The third pipe field is always survey-ingest-catalog even when the trace source is borehole or geochem.

## survey-ingest-catalog.json

Top-level field catalog_digest is sha256 hex over sorted canonical lines:

```
geo|<sample_id>|survey-ingest-catalog|<block_id>|<seq>|<recorded_at>|<formation_node>
```

The catalog traces array lists merged rows sorted by sample_id ascending.

## survey-seq-ledger.json

Top-level field survey_seq_ledger_digest is sha256 hex over sorted seqbook lines grouped by block_id:

```
seqbook|<block_id>|<max_seq>|<trace_count>
```

where max_seq is the highest seq among traces in that block and trace_count is the number of traces in that block.

Decoy formation files under /app/data/decoy must never appear in the catalog.
