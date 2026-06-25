The strace lane now reconstructs remote peers; extend the lsof lane and policy evaluator so continuation rows, paired snapshots, and out-of-run paths are enforced per `/app/docs/lsof_contract.md` and `/app/docs/audit_contract.md`.

Rebuild with `bash /app/scripts/build_all.sh`, then run `bash /app/scripts/milestone_probes.sh audit`. The audit must surface `descriptor_leak` on `burst_lane.md` with `fd_delta` `5`, `write_outside_run_dir` entries for `/etc/diffusion/cache/state.bin`, `/tmp/diffusion-run/scratch.dat`, and `/var/tmp/diffusion/spill.bin`, and must not emit `descriptor_leak` for `warmup_lane.md` where paired snapshots sit exactly at the leak threshold. The audit JSON must satisfy `/app/docs/audit_contract.md`, including matching `violation_count` and populated `violation_kinds` and `run_dir`.

Signal completion once those lsof-derived findings appear in `/app/output/policy_audit.json`.
