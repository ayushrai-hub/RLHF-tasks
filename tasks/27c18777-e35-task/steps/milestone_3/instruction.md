We’re ready to wire up the background triage run. Add `/app/src/TriageWorker.kt`; it should read `/app/terraform/outputs.json` for the incoming and prediction directories, load `/app/output/protocol-decisions.json`, and use `/app/models/classifier.bin`.

For every complete frame upload in the incoming directory, classify the PNG and read the matching metadata JSON. Apply the protocol in this order: untrusted sensors quarantine first, the raw softmax probability for the `strong_aurora` class at or above the approved threshold escalates, weak aurora below the approved temperature cutoff quarantines, and everything else archives. Ignore half-uploaded frames that do not have the matching metadata JSON yet.

Write one `[frame_id]_result.json` per processed frame under the configured predictions directory with `frame_id`, `aurora_class`, `probability`, `action`, and `flagged`. `flagged` is true for `quarantine` or `escalate`, false for `archive`. Also write `/app/output/run_summary.json` with `total_processed`, `escalated_count`, `quarantined_count`, and `archived_count`.

Ops reruns this with relocated directories, so each run should delete old `*_result.json` files from the configured predictions directory and summarize only the frames in that run’s incoming snapshot. Use a top-level `fun main()` so the worker runs as `TriageWorkerKt`.
