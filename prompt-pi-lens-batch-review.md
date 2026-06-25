# Terminus Pi-Lens Batch Review Prompt

Use this prompt for the Terminus accuracy **review loop** (`prompt.md` + `terminus-accuracy-review`) on the three Pi-Lens / api-context tasks.

---

## Invocation (copy-paste to agent)

```
Follow @prompt.md and @.cursor/skills/terminus-accuracy-review/SKILL.md exactly.

## Batch scope

Review these three Pi-Lens / api-context tasks independently — one `review-report.md` per task:

| Task dir | Declared difficulty | Category | Linked context IDs |
|----------|--------------------|-----------|--------------------|
| `@tasks/referral-attribution/` | hard | software-engineering | PPL-702, PPL-798, PPL-802, PPL-804, PPL-806, 1929576453 |
| `@tasks/referral-lock-state/` | hard | debugging | PPL-702, PPL-997, PPL-1000, PPL-1009, PPL-1011, 1929576453 |
| `@tasks/yt-nudge-scheduler/` | medium | software-engineering | PPL-1087, PPL-1189, experiment-youtube-live-chat-nudge-bot |

Do **not** use `@entire-report.txt` for any of these tasks — it describes a different task (Perl/Rails `tbench-task`). If no per-task agent report exists, mark agent/difficulty checkboxes UNCHECK with reason `no report supplied` and lower confidence.

## Per-task commands (run for each dir)

```bash
./scripts/terminus validate tasks/<task-name>
./scripts/terminus review tasks/<task-name>
./scripts/terminus oracle tasks/<task-name>    # if harbor/docker available
```

Deliverable: `<task-dir>/review-report.md` (sections 1–10, table-first, all 55 portal checkboxes).

## Pi-Lens family audit (apply to every task)

These tasks share a **tool-context** pattern: the issue text is intentionally thin; acceptance rules live only in linked Jira/Confluence content fetched via the offline API emulator at `http://127.0.0.1:8765`. Audit the family contract, not just generic Terminus compliance.

### A. Context retrieval design

| Check | What to verify | Proof target |
|-------|----------------|--------------|
| Issue does not restate rules | `instruction.md` names regression areas + linked IDs only; rules are in context docs | `instruction.md`, `cheat-sheet.md` |
| API-only retrieval path | Instruction tells agent to use `curl` against `127.0.0.1:8765` Jira/Confluence paths | `instruction.md` |
| Backing data not a shortcut | `environment/app/context/` (or `/opt/tool-context/`) is emulator backing store, not the intended solve interface | `task.toml` `[tool_context]`, Dockerfile, `bin/context-lookup` |
| Cross-document inference required | No single ticket/doc suffices; verifier needs rules from multiple IDs | `cheat-sheet.md`, `task-capabilities.md`, hidden tests |
| Context not leaked to agent | `cheat-sheet.md`, `SOURCE.md`, `task-capabilities.md`, `documents/` bundle not COPY'd into image | Dockerfile, build context |
| `allow_internet` | Must be `false` in `task.toml` `[environment]` | `task.toml` |

### B. Public vs hidden verifier split

All three declare `visible_tests = "public"` in `task.toml`.

| Check | What to verify |
|-------|----------------|
| Public smoke is intentionally weak | `public_tests/test_smoke.py` checks shape/existence only — not sufficient to pass task |
| Hidden tests encode rollout rules | `tests/test_outputs.py` asserts the real acceptance contract |
| Instruction warns agent | Instruction states public tests exist but hidden grading applies |
| No spec gap on hidden behavior | Every hidden assertion traces to a rule recoverable from linked context (via cheat-sheet as reviewer ground truth) |
| No phantom public requirements | Public tests do not assert behavior absent from instruction |

### C. Shared deliverable pattern

| Check | What to verify |
|-------|----------------|
| Entry point | `python3 /app/reconcile.py` writes `/app/output/report.json` |
| Determinism | Output stable for bundled fixtures; oracle derives answer (no hardcoded echo) |
| `test.sh` | Canonical reward block; no runtime `pip`/`apt`; runs reconcile before pytest |
| Verifier deps in image | `pytest==8.4.1` baked in Dockerfile, not installed in `test.sh` |

### D. Family consistency (cross-task)

Flag **Revise** if tasks in the same family diverge without justification:

- `tasks/referral-attribution` moves context to `/opt/tool-context/` and removes `/app/context`; the other two keep context under `/app/context/`.
- `tasks/referral-attribution` has a populated `cheat-sheet.md`; `tasks/referral-lock-state/cheat-sheet.md` is still `TODO (Phase 3)`.
- `tasks/referral-attribution` has `review/context-manifest.json`; siblings may not.

## Per-task acceptance contracts (use for spec↔test alignment §5)

### referral-attribution

Broken `apply_referral_events` in `/app/referral_processor.py`. Correct fix must:

- Accept `eventType` in `{"signup", "signin"}` (PPL-798)
- Use **pair-scoped** idempotency per referrer, not global `seen_referred_users` (PPL-802)
- Drop self-referral when `referredUserId == referrer userId` (PPL-804/PPL-806)
- Ignore unknown codes; deterministic sort: rows by `userId`, `referredUsers` sorted (PPL-702, PRD 1929576453)

Hidden tests must cover: signin credit (`u-zoe` → `u-alice`), cross-referrer credit (`u-zoe` → `u-bob`), self-referral drop, same-pair idempotency (`u-alice` = count 2 `[u-yuki, u-zoe]`), synthetic `build_report` pair-scoped case ignoring `purchase`.

### referral-lock-state

Broken lock/unlock logic in onboarding service. Correct fix must recover from linked tickets:

- Threshold boundaries lock at exact limits (PPL-1000 area)
- Referral quota unlocks all surfaces at exact target (PPL-1009/PPL-1011 area)
- Partial progress does not unlock exhausted surfaces

Hidden tests: `test_thresholds_lock_at_the_boundary`, `test_referral_quota_unlocks_all_surfaces_at_exact_target`, `test_partial_progress_does_not_unlock_any_exhausted_surface`. **Because cheat-sheet is TODO**, derive expected rules from `solution/solve.sh`, context docs, and tests; flag incomplete reviewer docs as Medium if they block fair adjudication.

### yt-nudge-scheduler

Broken scheduler timing in `/app/scheduler.py`. Correct fix must honor experiment doc + tickets:

- Minimum spacing ≥ configured interval (bundled: 10s between sends)
- Active poll window + post-poll grace window (sends at 20 and 70, not 80)
- Deterministic message-bank rotation (wrap, no random sort)

Hidden tests: `test_minimum_spacing_is_ten_seconds`, `test_scheduler_uses_grace_window_after_poll_end`, `test_messages_rotate_in_sequence`.

Agent calibration (if no harbor report): `pass_at_k_summary.csv` shows oracle 100%; gemini ~62.5% (referral-lock-state), 100% (yt-nudge-scheduler). Use for difficulty #45/#54 where available.

## Standard Terminus phases (per prompt.md)

Run phases 0–9 for each task. Pay extra attention to:

- **Phase 1:** No answer leakage in instruction; absolute paths; no step-by-step solve script
- **Phase 2:** Digest-pinned `FROM`; `tmux` + `asciinema` present; no `COPY` of `tests/` or `solution/`; no AI scaffolding in image
- **Phase 3:** Oracle computes from fixtures + context rules, not `cat` of expected JSON
- **Phase 4:** Every `test_*` has docstring; behavior tests not implementation grep; reward.txt on failure
- **Phase 5:** `category`, `difficulty`, `tags` (`pi-lens`, `api-context`) match content; timeouts plausible
- **Phase 7:** Adjudicate any supplied per-task LLMaJ/agent claims in §3 table — artifacts win over reports
- **Phase 8:** Cheating closed: agent cannot pass smoke alone; context files in image must not expose answers without API traversal

## Disposition rules (per task)

| Condition | Disposition |
|-----------|-------------|
| Hidden test asserts behavior not recoverable from linked context | **Revise** (Test Alignment / Instruction Styling) |
| `cheat-sheet.md` missing/TODO and you cannot verify spec↔test from artifacts | **Revise** or Accept with Medium note on reviewer docs |
| Public smoke passes but hidden contract is fair and oracle passes | Accept candidate |
| Worst-model pass rate >80% | **Revise** (Task Difficulty) or Decline if trivial |
| Missing `allow_internet = false`, unpinned FROM, runtime test installs, no reward on failure | **Revise** (Environment / Pinning / Test Build) |

Tag every blocker with error categories from `prompt.md`.

## Chat output (after all three reports)

For **each** task, reply with only:

1. Path to `review-report.md`
2. Disposition (Accept / Revise / Decline)
3. Error categories (`none` or comma-separated)
4. CHECK numbers
5. UNCHECK numbers
6. One-line summary

Then a **batch summary table**:

| Task | Disposition | Main blocker (if Revise) | Tier match |
|------|-------------|--------------------------|------------|
| referral-attribution | … | … | … |
| referral-lock-state | … | … | … |
| yt-nudge-scheduler | … | … | … |

Do not dump full reports in chat — files are the deliverable.
```

---

## Usage notes

1. **One report per task** — the review loop is per-folder; do not merge into a single `review-report.md`.
2. **`entire-report.txt` is out of scope** for these three tasks unless you add task-specific harbor/LLMaJ exports.
3. **Family-specific checks** (context API, public/hidden split, cross-doc inference) are the main delta from generic `prompt.md` — generic Edition 2 checks still apply.
4. **`tasks/referral-lock-state/cheat-sheet.md` is incomplete** — the prompt tells the reviewer to derive rules from solution + tests and flag that gap.

## Related files

| File | Purpose |
|------|---------|
| `prompt.md` | Base Terminus accuracy review prompt |
| `.cursor/skills/terminus-accuracy-review/SKILL.md` | Review skill and deliverable format |
| `tasks/referral-attribution/` | Task 1 |
| `tasks/referral-lock-state/` | Task 2 |
| `tasks/yt-nudge-scheduler/` | Task 3 |
