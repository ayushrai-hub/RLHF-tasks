# Build driver CLI

All paths are under `/app/environment` unless noted.

## Fast rebuild

```bash
/app/environment/bin/bld_host [cap_label]
```

Optional positional `cap_label` re-renders the version constants header then performs an incremental rebuild of `app_v1` and `app_v2`.

## Incremental-only rebuild

```bash
/app/environment/bin/bld_host --incremental-only
```

Runs a quick rebuild without re-rendering the version constants header. Verifier tests use this mode to confirm object reuse when inputs are unchanged.

## Pristine rebuild

```bash
/app/environment/bin/bld_host --pristine [cap_label]
```

Wipes `/app/environment/var/objs` and `/app/environment/var/bins`, renders the header, then rebuilds both targets from scratch.

## Dependency audit

```bash
/app/environment/bin/bld_host --audit-deps <target> <output.json>
```

Writes the resolved dependency path list for `app_v1` or `app_v2` to the given JSON file. Used during diagnosis to compare the scanned graph against regenerated inputs.

## Trace recorder

```bash
/app/environment/bin/trace_host [/app/environment/data/run_plan.json]
```

Regenerates `/app/output/rebuild_trace.json` by executing each plan in the JSON matrix (default plan file shown above).

## Equal-second helper

```bash
/app/environment/scripts/touch_same_sec.sh [/app/environment]
```

Aligns modification times on the generated constants header and the shared widget object file for plans that require equal-second sequencing.

## Compile journal

Each compile or skip decision appends one line to `/app/environment/var/stats/compile.log` as `action`, `source_rel`, and `mode` (`fast` or `pristine`). The journal resets only when removed explicitly or when the log file is deleted.

## Generation ring

Quick link steps record blob paths and generation tags in `/app/environment/var/slots/gen_ring.bin`. The ring persists across quick rebuilds until explicitly cleared.

Each tag is the live header generation for `/app/environment/var/gen/version_slot.h`, computed as `(st_mtime XOR st_size) mod 2^32` from `stat` on that file. After the constants header is re-rendered, every ring entry must be cleared or updated so its stored tag matches the new live generation.

## Verifier note

Host pytest may pass internal reporting flags (for example `--ctrf`); agents only need the driver paths documented above.
