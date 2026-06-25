The trace index is available; next rebuild the strace reconstruction lane so `connect` peers and out-of-run `openat` paths are parsed from fenced excerpts per `/app/docs/strace_contract.md`.

Rebuild with `bash /app/scripts/build_all.sh`, then run `bash /app/scripts/milestone_probes.sh audit`. The audit probe must write `/app/output/policy_audit.json` with `schema_tag` `tb3-kdiff-trace-02`, `run_dir` `/var/lib/diffusion-runs/current`, and `socket_rows` listing exactly one non-loopback peer (`93.184.216.34:443`) while omitting loopback peers such as `127.0.0.1`. Out-of-run `openat` paths must surface as `write_outside_run_dir` violations with the bare path as `detail`, including `/etc/diffusion/cache/state.bin`, `/tmp/diffusion-run/scratch.dat`, and `/var/tmp/diffusion/spill.bin` from their respective runbooks.

Signal completion once the audit probe shows the remote peer, excludes loopback connects, and reports those out-of-run paths.
