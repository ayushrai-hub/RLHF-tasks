# The Relic Vault — Season Migration

You've inherited **Relic Vault**, a small terminal roguelike written in C (an
ncurses front-end, a `Makefile`, a legacy hand-written room-table loader, and a
scripted replay driver). The new season has arrived not as a tidy table but as a
**mixed archive** — parquet, CSV, JSON, and ASCII tile maps — that has to be
*migrated* into the game's binary database before anyone can play it.

A half-finished, Polars-based migration harness ships with the repo. Your job,
across three milestones, is to finish the migration and wire the new database into
the engine. Everything you need is already in the container — there is no network
access.

## The lay of the land (absolute paths)

- `/app/archive/` — the raw season archive:
  - `/app/archive/rooms.csv` — chamber table (old PascalCase headers).
  - `/app/archive/monsters.parquet` — guardian table (Apache Parquet).
  - `/app/archive/relics.json` — relic records (camelCase keys).
  - `/app/archive/tiles/room_<room_id>.txt` — one ASCII tile map per chamber.
  - `/app/archive/expedition.script` — the replay driver's scripted run (milestone 3).
- `/app/harness/migrate.py` — the **partially implemented** Polars migration harness.
- `/app/engine/` — the C engine: `relicvault.c`, `legacy_rooms.{c,h}`, `Makefile`.
- `/app/docs/chronicle.md` — the **designer's chronicle**. It is long and rambling,
  but the load-bearing rules are gathered into four authoritative **Appendices**
  at the very end. Read them carefully — they are the single source of truth for
  every number the graders check.
- `/app/out/` — write all of your output artifacts here (create it if needed).

## Milestone 1 — Decode Archive Schema

Finish the harness so that

```
python /app/harness/migrate.py schema --archive /app/archive --out /app/out
```

reads and normalises all four sources and writes a canonical schema report to
**`/app/out/schema_report.json`**.

The report is a JSON object whose keys are the four normalised table names
`monsters`, `relics`, `rooms`, and `tiles`. Each maps to an object of the form:

```json
{
  "columns": ["<normalised column names, sorted alphabetically>"],
  "dtypes": ["<canonical dtype of each column, in the same order>"],
  "row_count": 0,
  "fingerprint": "<64-hex SHA-256 of the canonicalised rows>"
}
```

The exact normalisation contract — how PascalCase/camelCase column names become
`snake_case`, how each column's `int`/`str` dtype is decided, and how the `tiles/`
directory becomes a `{room_id, hazard_count}` table — is **Appendix I of
`/app/docs/chronicle.md`**, the single source of truth. The report must be
serialised exactly as `json.dumps(report, sort_keys=True, indent=2)` followed by a
single trailing newline.

Several of Appendix I's rules are deliberately counter-intuitive; the ones most
easily gotten wrong are:

- **`tiles` hazard_count (Rule I.3).** Count **only** the spike glyph `^` in each
  tile map. Every other glyph (`#`, `~`, `*`, walls, dots, …) is ignored — do not
  count them as hazards.
- **dtypes of id columns (Rule I.2).** A column is `int` only if every value is a
  whole number — **except** any column whose normalised name ends in `_id`
  (`room_id`, `monster_id`, `relic_id`), which is a catalogue identifier and is
  **always** `"str"`, even though its values are digits.

The per-table **`fingerprint`** (Appendix I, Rule I.4) is computed exactly as
follows (note steps 3's key omission):

1. Order the table's columns **alphabetically** by their normalised name.
2. Sort the rows **ascending by primary key** — `room_id` for `rooms` and `tiles`,
   `monster_id` for `monsters`, `relic_id` for `relics`.
3. Render each row as `col=value` for every **non-key** column in that alphabetical
   order, joined with a single pipe `|` — the **primary-key column is omitted** from
   the row string (it only orders the rows; it is not hashed). Integers are their
   base-ten digits, strings exactly as stored (no quoting, no separators other than
   `=` and `|`).
4. Join the row strings with a single newline `\n` (no trailing newline) and take
   the **lowercase hex** SHA-256 digest of the UTF-8 bytes.

Keep the harness's `schema`/`pack` sub-commands and its `--archive` / `--out`
flags intact and **data-driven**: the grader re-runs your harness on additional,
unseen archives, so nothing about the shipped data may be hardcoded.

When `/app/out/schema_report.json` is in place and correct, this milestone is done.
