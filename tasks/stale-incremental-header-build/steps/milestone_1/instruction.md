An offline C/CMake workspace lives under `/app/environment`. Host tools `/app/environment/bin/bld_host` and `/app/environment/bin/trace_host` drive quick and full rebuild paths for link targets `app_v1` and `app_v2`. Version labels are rendered into `/app/environment/var/gen/version_slot.h`.

Operators report three failure modes after cap-label bumps on the quick path: linked binaries carry older capability labels than the constants header, quick-path digests diverge from full-path digests, and rolling back to a prior cap label without a full wipe can leave stale linked output while the ring file under `/app/environment/var/slots/` still records prior generations. Full from-scratch rebuilds always match the header.

Do not modify anything under `/app/environment` during this step.

Regenerate `/app/output/rebuild_trace.json` with `/app/environment/bin/trace_host` and `/app/environment/data/run_plan.json`. See `/app/environment/docs/trace_contract.md` for trace rows and `/app/environment/docs/bld_cli.md` for driver usage.

Reproduce the header-bump plan quick path (`cap_r1` pristine baseline, then quick rebuild with the plan cap label) before reading capability state from the generated header—not after the full multi-plan trace. Hand-written traces are not sufficient; do not wipe the artifact tree between those steps.

Write `/app/output/quick_full_delta.json` summarizing which plans in the live trace still show quick-vs-full digest inequality. Include `mismatch_count` and `plans_with_mismatch` (each entry names `plan_id` and the `targets` where digests differ). List mismatched plans in the same order they appear in `/app/environment/data/run_plan.json`.

Write `/app/output/slot_ring_audit.json` after the same reproduction sequence. Inspect `/app/environment/var/slots/gen_ring.bin` against the live header generation. Each `entries` item records `blob_path`, `stored_gen`, `live_gen`, and `gen_aligned`. Set `any_stale_gen` when any stored generation disagrees with the live header generation. After the cap-bump quick rebuild, expect ring entries for both link targets with misaligned generations.

Write `/app/output/journal_surfaces.json` capturing compile-journal tail behavior for `app_v1/main.c` after the cap-bump quick rebuild. Use `surfaces` as a list of objects with `source_rel` and `last_action_skip` (true when the journal tail shows a skip for that source despite the header bump).

After the cap-bump reproduction sequence, `app_v1/main.o` under `/app/environment/var/objs/` must remain older than the regenerated `/app/environment/var/gen/version_slot.h` (compare modification times). That stale-object versus fresh-header state is part of the broken quick-path signature you are documenting.

Signal completion when all four output files reflect the broken quick-path behavior on the live workspace.
