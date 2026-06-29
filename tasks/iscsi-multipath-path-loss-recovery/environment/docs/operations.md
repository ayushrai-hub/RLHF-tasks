# Scenario fixture glossary

Bundled scenarios live under `/app/environment/data/scenarios/` as JSON files named `{scenario_label}.json`. Labels s01 through s06 ship with the image. Verifier runs may inject additional scenario JSON files into a temporary sweep directory; the pipeline must process any valid fixture with the same schema.

## Fixture fields

| Field | Type | Role |
|-------|------|------|
| scenario_label | string | File stem and row key |
| table_gen | integer | Generation token in digest composition |
| crash_mid | boolean | Interrupted failback left affinity before dataplane in the journal |
| active_path_mask | integer | Bitmask of paths currently marked active |
| target_path_mask | integer | Bitmask of paths the failback should converge to |
| stranded_path_mask | integer | Standby paths stranded off the active set |
| alua_base_ms | integer | Baseline ALUA reprobe latency |
| flush_bump | integer | Per-scenario queue bump override; zero loads registered depth from `/app/environment/config/failback_flags/` |
| failback_early | boolean | Early failback routing still influences spread penalties |
| summary_green_view | boolean | Fabric summary claims balanced spread |
| retain_seq | integer | Non-zero applies right-shift (`retain_seq % 8`) to stranded_path_mask before retain merge |
| gate_hold | boolean | ALUA gate may defer queue refresh until finalize |

Path masks are unsigned integers (bit N means path N). Hex report fields encode masks in lowercase hex without a `0x` prefix.

Interrupted failback bookkeeping may persist under `/app/var/failback_journal/` as `{scenario_label}.tail` JSON (for example `s02.tail`). Tail files record prior replay bookkeeping only; a successful segplay replay clears stale tails and must not let an inflated tail `replay_epoch` change the emitted row value.

## Row emission semantics

- replay_epoch — number of checkpoint segment kinds replayed for the scenario during segplay. Non-crash scenarios report 0. Crash-mid scenarios replay segments in seq order (affinity before dataplane) and report 2 because both kinds count.
- segment_seq_crc — fingerprint of the segment kind list stored for the scenario: [dataplane] when crash_mid is false; [affinity,dataplane] when crash_mid is true.
- pre-affinity/pre-spread — pre_affinity = stranded_path_mask & dataplane_mask. pre_spread = popcount(dataplane_mask & pre_affinity).
- retain stage — if retain_seq <= 0, retained_affinity = stranded_path_mask & dataplane_mask. If retain_seq > 0, shift = retain_seq % 8 and retained_affinity = (stranded_path_mask >> shift) & dataplane_mask.
- route/filter stage — route base is always raw stranded_path_mask (not retained_affinity). route_dataplane = target_path_mask when non-zero, else active_path_mask. With failback_early=true, filter decisions use pre_spread. routed_affinity = stranded_path_mask when filter_hit=true; otherwise routed_affinity = stranded_path_mask & route_dataplane.
- queue stage — queue_mask starts from retained_affinity. Refresh intersects queue_mask with dataplane_mask. final_affinity = routed_affinity & queue_mask.
- path_overlap_index — popcount(dataplane_mask & final_affinity) in the emitted row.
- ALUA penalty — start from alua_base_ms. Add flush_bump*7 when final_affinity is not a subset of dataplane_mask. Add flush_bump*3 when summary_green_view=true and penalty spread index is zero. penalty_spread uses pre_spread when failback_early=true, else final popcount spread.
- session_token_hex — first eight hex chars of sha256sum over table_gen|active_path_hex|standby_path_hex.
- digest_hex — first sixteen hex chars of sha256sum over the pipe-separated row fields listed in `/app/environment/emit/digest.go`.

Failback flag fragments under `/app/environment/config/failback_flags/` carry `registration_order` and `completion_depth`; effective depth follows highest registration order, not filename sort.
