# Milestone 2 — Migrate Puzzle Database

With the archive decoded, migrate it into the engine's binary database. Finish the
harness so that

```
python /app/harness/migrate.py pack --archive /app/archive --out /app/out
```

writes **two** artifacts: the little-endian image **`/app/out/vault.pack`** and the
consulted-scope audit **`/app/out/consulted.json`**.

`vault.pack` describes the vault as an ordered sequence of **chambers**, one per
room. For each chamber the harness must derive — by combining the room's biome,
its guardian (from `monsters.parquet`), its relic (from `relics.json`), and the
tile **hazard count** — the fields `guard_hp`, `guard_atk`, `relic_worth`, the
`biome_code`, the `sigil`, the room name, and the guardian species, and emit them
in `chamber_index` order.

Note the archive is a *mixed* dump: a room may list **several candidate guardians
and relics**, and some monster/relic rows belong to **no** room at all. Each
chamber takes exactly one guardian and one relic per the selection rule.

- The chamber ordering, the derivation arithmetic (biome modifiers, hazard
  adjustments, no-guardian / no-relic cases), and the **candidate-selection rule**
  are **Appendix II of `/app/docs/chronicle.md`**.
- The exact byte layout of the header, the 53-byte chamber records, and the footer
  is **Appendix III**.
- The contents and exact JSON format of **`/app/out/consulted.json`** — the audit
  of which records the migration *consulted* — are **Appendix V**.

Appendix II is short but several of its rules are deliberately counter-intuitive —
the **chamber ordering** (how chambers that share a `depth` are tie-broken), the
**guardian stat** arithmetic, the **relic worth** arithmetic, and the
**candidate-selection** rule. And `consulted.json` (Appendix V) is **not** simply
the list of selected guardians/relics — read Appendix V carefully for exactly which
records count as consulted. In every case the "obvious" implementation gives the
wrong bytes; the grader compares **both** outputs byte-for-byte.

As before, keep the logic data-driven — the grader migrates additional unseen
archives with your harness and compares the resulting artifacts byte-for-byte.

This milestone is complete when `/app/out/vault.pack` and `/app/out/consulted.json`
are both the correct migration of the archive.
