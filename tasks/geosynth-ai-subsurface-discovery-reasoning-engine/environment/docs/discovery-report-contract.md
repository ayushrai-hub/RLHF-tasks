# Discovery report contract

branch-formations writes /app/state/formation-compose-staging.json using hypothesis_priority from formation-governance.json.

## Binding summary (read first)

| Rule | Requirement |
|------|-------------|
| compose array order | compose[0] is the first block_id listed in hypothesis_priority, compose[1] is the second, and so on |
| iteration direction | walk hypothesis_priority in JSON array order from first element to last (do not reverse the list) |
| digest vs array | formation_compose_digest hashes sorted compose lines; the compose array itself keeps hypothesis_priority order |
| live policy | branch-formations must read the current formation-governance.json on disk (verifier may swap hypothesis_priority for hidden cases) |

When hypothesis_priority lists shale-margin-east before copper-belt-north, compose[0].block_id must be shale-margin-east after branch-formations runs.

## formation-compose-staging.json

Field formation_compose_digest is sha256 hex over sorted compose lines built from depth epochs and evidence_kind mapping per block.

copper-belt-north first evidence step maps tr-gc-001 to pathfinder-spike evidence_kind.

export-discovery writes /app/output/geosynth-discovery-report.json with discovery_store geosynth-bundled.

discovery_fingerprint derives from sorted chain|block_id|step|sample_id lines only (not epoch_digest).

discovery-export-bind.json uses status finalized and consolidation_epoch 3.

guard-hypotheses accepts basalt-deep-west with shale-margin-east and basalt-deep-west with copper-belt-north on bundled data.

confidence_floor caps confidence_margin per block per confidence-witness-math.md.
