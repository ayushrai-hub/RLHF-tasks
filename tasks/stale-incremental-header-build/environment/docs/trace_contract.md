# Rebuild trace contract

`/app/output/rebuild_trace.json` is produced only by `/app/environment/bin/trace_host` (optional first argument overrides the default plan file `/app/environment/data/run_plan.json`).

## Top-level shape

```json
{
  "rows": [ { "...": "..." } ]
}
```

## Row fields

| Field | Type | Meaning |
|-------|------|---------|
| `plan_id` | string | Plan identifier from the run plan. |
| `target` | string | Link target name (`app_v1` or `app_v2`). |
| `fast_digest_hex` | string | Lowercase SHA-256 hex digest of the fast-rebuild linked binary for that plan/target. |
| `pristine_digest_hex` | string | Lowercase SHA-256 hex digest of the pristine-rebuild linked binary for the same plan/target. |
| `capability_tag` | string | Label embedded in the fast-rebuild binary (the `@CAP:` string payload). |

## Matrix law

For every row emitted for a plan in the run plan, `fast_digest_hex` must equal `pristine_digest_hex`, and `capability_tag` must match the plan's `cap_value` after the scripted edits when the build graph is correct.

Plan `cap_value` strings in `/app/environment/data/run_plan.json`:

- `header_bump` → `cap_r2`
- `unchanged_control` → `cap_r2`
- `cap_rollback` → `cap_r2` (final cap after the mid-sequence bump and rollback quick paths)
- `same_second_seq` → `cap_r3`

The `cap_rollback` plan runs a pristine baseline, a quick bump to `cap_r3`, then a quick return to `cap_r2` without wiping the artifact tree before measuring rows.

## Rejected shortcuts

- Running only pristine rebuilds while leaving fast rows stale.
- Deleting the entire artifact tree between steps inside driver sources or helper scripts used by the verifier.
- Globally disabling the incremental path in driver sources (for example environment variables that force every step down the pristine-only path).
- Delegating the fast rebuild path to pristine rebuild internally while still emitting fast trace rows.
- Forcing unconditional recompilation on every fast rebuild when inputs are unchanged (compile journal shows only `compile` lines with zero `skip` lines on back-to-back fast runs).

## Diagnosis artifacts (milestone 1)

Milestone 1 writes observation JSON under `/app/output/` derived from live tool output. See milestone 1 instructions for paths and field semantics. The generation ring persisted under `/app/environment/var/slots/gen_ring.bin` tracks link-generation tags across quick rebuilds; diagnosis must compare stored ring entries against the live header generation after reproducing the header-bump quick path.

## Header generation tag

The live header generation is a 32-bit unsigned tag derived from the generated constants header at `/app/environment/var/gen/version_slot.h`:

```
live_gen = (st_mtime XOR st_size) mod 2^32
```

Use the header file's modification time and byte size from `stat`. Every generation ring entry's stored tag must match the live tag after a cap-bump quick rebuild refreshes the header. When the header is re-rendered, stale ring entries must be cleared or rewritten so all recorded blob paths share the current live tag.

## Transitive header staleness on quick rebuild

Re-rendering the constants header during a quick rebuild must force recompilation of every translation unit whose include graph reaches that header, not only direct includers. A source that includes an intermediate header which itself depends on the generated constants is still stale when its object file predates the refreshed header.

For the cap-bump recovery sequence (`cap_r1` pristine baseline, then quick rebuild with `cap_r2`):

- The compile journal must include a fast-mode `compile` line for `app_v1/main.c` (`main.c` includes `libcore/widget.h`; the widget library includes the generated constants header).
- `/app/environment/var/objs/app_v1/main.o` must not be older than `/app/environment/var/gen/version_slot.h` (compare modification times from `stat`).

The quick path must still compile fewer units than a pristine rebuild of the same targets once transitive staleness is handled correctly.
