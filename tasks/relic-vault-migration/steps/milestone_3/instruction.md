# Milestone 3 — Integrate Terminal Expedition

Time to play the migrated vault. The replay driver in `relicvault.c` loads
`vault.pack` but does **not** yet enforce the expedition rules. Extend the C
engine so it replays a scripted expedition and records a transcript.

Build it with the shipped `Makefile`:

```
make -C /app/engine
```

which must produce the executable **`/app/engine/relicvault`**. Then run:

```
/app/engine/relicvault --replay \
    --pack /app/out/vault.pack \
    --script /app/archive/expedition.script \
    --out /app/out/transcript.txt
```

so that **`/app/out/transcript.txt`** holds the full transcript of the scripted
run.

The engine reads the script one action per line (`ADVANCE`, `STRIKE`, `GRAB`,
`BRACE`; blank lines and `#` comments are skipped). It tracks the delver's health,
attack, score, and position, resolves combat against each chamber's guardian,
lets the delver claim relics and brace for health, and appends exactly one
transcript line per action followed by a final `RESULT` summary line.

The complete expedition rites — the starting stats, the combat and relic and
bracing rules, the win/lose handling, and the **exact transcript line format**
(field widths and the `RESULT` line) — are **Appendix IV of
`/app/docs/chronicle.md`**. The transcript must match it character-for-character.

Appendix IV's combat rites contain several subtle, easily-missed mechanics — among
them the delver's **non-monotonic `atk`** (it both rises and falls over the course
of a fight) and a **kill-streak bonus** that pays into the score on consecutive
slayings. The natural/obvious implementation of each is wrong. Read Appendix IV
closely and reproduce every rule exactly — the transcript is graded
character-for-character, so a single wrong `atk` or `score` value fails the run.

The expedition logic must live in the **C engine** (the grader recompiles nothing
for you, but it does re-run your built `/app/engine/relicvault` on additional,
unseen vault/script pairs), so keep it a real, rule-driven simulation rather than
a transcribed answer.

This milestone is complete when `/app/out/transcript.txt` is the correct transcript
of the scripted expedition over `/app/out/vault.pack`.
