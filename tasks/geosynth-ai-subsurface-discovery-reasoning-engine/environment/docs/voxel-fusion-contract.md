# Voxel fusion contract

fuse-voxels reads the depth epoch ledger, materializes the staging snapshot at /app/state/voxel-staging-snapshot.json, then writes the fusion graph at /app/state/voxel-fusion-graph.json

## Binding summary (read first)

Within each exploration block, sort traces by (seq ascending, sample_id ascending) before edge enumeration. Emit a directed edge for every forward pair (i, j) with i less than j in that ordering, not only adjacent neighbors. Deduplicate edges globally and sort by (from, to). Weight each edge using the highest-priority modality on either endpoint per the priority table below.

## Staging snapshot

voxel-staging-snapshot.json is written before voxel-fusion-graph.json.

Fields include staging_digest (sha256 hex over sorted stage|block_id|formation_node|sample_id lines built from epoch sample_ids) and bound_epoch_digest copied from depth-epoch-ledger.json epoch_digest.

## Trace ordering within a block

For edge enumeration, group traces by block_id. Within each block sort traces by (seq ascending, sample_id ascending). recorded_at must not be used as the within-block sort key.

## Forward pair enumeration

Within each block, emit one directed edge for every forward pair of distinct sample_ids where the later trace appears after the earlier trace in the block sort order (all pairs with i less than j, not only adjacent neighbors).

Deduplicate edges globally by (from, to). Sort final edges by (from, to) ascending.

Each edge object includes from, to, block_id, weight, and forward_span (index distance j minus i in the block ordering).

## Modality weight priority

Load coefficients from /app/data/policies/modality-weights.json: borehole 0.68, seismic 0.55, gravity 0.42, magnetic 0.38.

For each edge, inspect the source modality of both endpoint traces. Assign the weight from the highest-priority modality present on either endpoint using this priority order:

1. borehole (if either endpoint source is borehole)
2. else seismic (if either endpoint source is seismic)
3. else gravity (if either endpoint source is gravity)
4. else magnetic (all remaining sources including geochem and hyperspectral)

Example: tr-gc-001 (geochem) to tr-bh-001 (borehole) uses borehole weight 0.68 because borehole is the higher-priority modality on either endpoint.

## voxel_graph_digest

voxel-fusion-graph.json includes voxel_graph_digest (sha256 hex), bound_staging_digest, edges array, and graph_source geospatial-fusion.

Digest lines use Python str() on the weight float (no custom rounding formatter):

```
voxel|<from>|<to>|<block_id>|<weight>
```

Lines are sorted lexicographically before hashing.

Example line: voxel|tr-gc-001|tr-bh-001|copper-belt-north|0.68
