# Confidence witness math

confidence_margin for each block equals max(1.0 minus mean prospect_index across that epoch sample_ids, confidence_floor).

## confidence-margin-ledger.json

Field margin_table_digest is sha256 hex over sorted lines:

```
conf|<block_id>|<margin>
```

where margin is formatted with exactly four digits after the decimal point using Python format spec :.4f (for example conf|copper-belt-north|0.4200).

discovery-export-bind.json binds discovery_fingerprint, formation_compose_digest, and guard_digest at consolidation_epoch 3.
