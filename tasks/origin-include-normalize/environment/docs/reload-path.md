# znctl reload reconciliation

This document defines reload-time behavior. Binary layouts and JSONL field names live in `toolchain.md`.

## Reload pipeline

`reload` repeats master ingestion and scope merge, reloads the prior `material.bin` snapshot into replay memory when that file exists, then runs warm reconciliation before emitting products. When `material.bin` is absent, replay is empty and warm carry eligibility must fall through to seeded totals after floor clamping.

Warm reconciliation executes **two carry passes** per reload command. Phase `0` warm events are ignored. Phase `1` events restore packet and byte totals from the loaded material snapshot for the matching `key`; they restore ttl from the replay packet field and must not replace the current canonical body string or anchor scope from the freshly ingested master text.

Each reload command increments an internal epoch counter before warm work begins. Carry comparisons in the first warm pass must use the freshly merged row state produced by the current command, not stale pre-ingestion handles.

## Carry eligibility — first pass

For each active row, emit a phase `1` carry event when replay contains the same `key` **and** the replay canonical body string equals the row's current canonical body string.

Apply phase `1` events through the event stage, then persist the scope journal (see below), then raise non-carried rows to at least the snap floor.

## Scope journal

After the first carry pass and its event application, write `<workroot>/.state/scope-journal.bin`:

- magic `ZNWJ`, version `1`, little-endian row count
- per row in current lane order: key length, **key** bytes, carried u8 (`1` when that `key` received a phase `1` event in the first pass)

Journal identifiers are always rule keys from `@key=`, never mark labels.

## Carry eligibility — second pass

Emit phase `1` events only for rows whose `key` is marked carried in the scope journal. Apply events, then apply the same floor rule as the first pass using the journal carried set rather than recomputing eligibility from replay.

## Floor interaction

After each carry pass, rows that did **not** receive a phase `1` event in that pass are raised to at least the snap floor on ttl (packet field). Rows that did receive carry keep restored totals even when already above the floor.

Scope merge (before warm reconciliation) replaces seeded ttl totals per `key` from the snap packet field and must not retain higher in-memory totals when the snap row changes. Master rows with no scope row keep parsed ttl through normalize; reload may leave them below the floor until the post-pass floor step runs.

## Journal rebuild

When `scope-journal.bin` is absent at the start of a reload command, the first pass recomputes carry eligibility from replay body equality. When the journal is deleted between reload commands on an otherwise unchanged workroot, a subsequent reload must rebuild identical journal flags and product rows.

When both `scope-journal.bin` and `material.bin` are absent, reload must still converge to the same catalog rows and equivalence observations as a prior reload that had both files present, using scope merge and floor clamping alone. Journal carry flags may differ when replay is empty.

## Include anchor resume

Ingestion must resume the pre-include anchor after each `$INCLUDE` returns. Cold preprocessing must canonicalize each row against the anchor that was active when that row was parsed, not a single global anchor taken from another fragment. Reload carry must not pin anchor scope from replay snapshots across include boundaries when master text has been re-ingested with a different effective anchor stack.

## Working edge list

Lane binding consumes only root-anchored include edges whose ordinal is valid for the active root master path. Ordinal zero is a legal include position and must not be dropped when building the working edge list.
