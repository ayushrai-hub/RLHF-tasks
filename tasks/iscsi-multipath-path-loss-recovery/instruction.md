After an iSCSI path-loss storm, multipath failback still looks healthy while I/O fails. The nightly failback report shows flat overlap counts and stale ALUA reprobe values.

Fix Go under /app/environment so pathfb-sweep regenerates /app/output/path_failback_report.json. Hand-written JSON is insufficient; the verifier rebuilds and reruns the sweep.

/app/bin/pathfb-sweep --scenarios-dir /app/environment/data/scenarios --out /app/output/path_failback_report.json
/usr/bin/go build -C /app/environment -o /app/bin/pathfb-sweep /app/environment/cmd/pathfb_sweep

Output JSON has a runs array. Each row includes scenario_label, path_overlap_index, active_path_hex, standby_path_hex, alua_reprobe_ms, digest_hex, replay_epoch, segment_seq_crc, and session_token_hex. path_overlap_index is the popcount of the final mask intersection; hex masks are unsigned bitmasks in lowercase hex without 0x. Digest composition is defined in /app/environment/emit/digest.go (sha256sum over UTF-8 pipe-separated fields).

Bundled scenarios are s01, s02, s03, s04, s05, and s06; the verifier may also inject additional scenario files (for example s07) in the sweep directory. Reconciliation rules:
- standby_path_hex must be a subset of active_path_hex.
- path_overlap_index must match popcount(active_path_mask & final_standby_mask).
- replay_epoch counts replayed checkpoint segment kinds (0 when crash_mid is false; 2 when true because affinity and dataplane both count in seq order).
- segment_seq_crc fingerprints segment-kind order: non-crash scenarios use [dataplane]; crash-mid scenarios use [affinity, dataplane].
- stale journal tail files must not inflate replay_epoch after successful replay.
- pre_affinity = stranded_path_mask & dataplane_mask; pre_spread uses pre_affinity.
- routing base is always the raw stranded_path_mask (not retained affinity): routed = stranded when filter hits, else routed = stranded & route_dataplane.
- queue_mask starts from retained_affinity and refresh intersects queue_mask with dataplane_mask; final_standby_mask = routed & queue_mask.
- ALUA penalty uses pre_spread when failback_early=true, else final spread.
- digest_hex must stay stable across three consecutive sweeps.

Fixture fields and emission semantics are in /app/environment/docs/operations.md. Grade with bash /tests/test.sh. Harbor passes --ctrf to pytest for logging.
