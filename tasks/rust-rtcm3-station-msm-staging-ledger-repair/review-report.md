# Terminus Review Report: rust-rtcm3-station-msm-staging-ledger-repair

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (submission export 100% 3/3; local Docker unavailable) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Strong Rust RTCM3 ingest/staging/ledger repair task with digest-pinned offline env, comprehensive behavioral tests, and compliant flat non-milestone rubric (25 positive pts, 3 negatives). Automated audit #14/#20 are false positives — pip deps are `==`-pinned in `requirements.lock` and pytest is baked into `/opt/verifier-venv`. No High or Medium blockers.

**Insights (concise):**

- Task folder renamed from `rust-rtcm3-station-msm-staging-ledger-repair.` (trailing dot) → `rust-rtcm3-station-msm-staging-ledger-repair`.
- Submission export relocated to `terminus/reviews/rust-rtcm3-station-msm-staging-ledger-repair-entire-report.txt`; workspace `entire-report.txt` symlink updated.
- Rubric uses flat non-milestone format (single `# Rubric` block, no `# Rubric 2+`); 25 pts ≤ 40 cap.
- `ingest` pipeline documented in `cli-contract.md:11`; instruction mandates matching all `/app/docs/` contracts — not a spec-gap blocker.
- Worst-model 60% (medium tier); declared `hard` vs platform `medium` is informational only.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | High severity: none; structurally sound (ChatGPT) | Agree | `task.toml:17` `allow_internet=false`; `Dockerfile:16-26` tmux+asciinema; `.dockerignore:13-14`; `test.sh:37-47` offline rebuild+pytest |
| 2 | Medium severity: none (ChatGPT) | Agree | No spec-test High gaps (section 5); rubric 25/40 |
| 3 | Flat non-milestone rubric: 25 pts, 3 negatives (ChatGPT) | Agree | `entire-report.txt:277-287`; `task.toml:9` `number_of_milestones=0` |
| 4 | Optional: difficulty hard vs MEDIUM (ChatGPT) | Agree (not blocker) | `task.toml:6`; `entire-report.txt:14`; worst-model 60% |
| 5 | Optional: spell ingest pipeline in instruction (ChatGPT) | Partially agree (Low) | `cli-contract.md:11`; `instruction.md:3` contract mandate |
| 6 | Dockerfile digest-pinned Rust base (ChatGPT) | Agree | `Dockerfile:1,14` `@sha256:9f841bbe…` |
| 7 | Decision Accept (ChatGPT) | Agree | Artifacts support Accept |
| 8 | Automated audit #14 unpinned pip | Disagree | `requirements.lock:1-6`; `Dockerfile:28-30` |
| 9 | Automated audit #20 pytest not in image | Disagree | `requirements.lock:5` `pytest==9.0.3`; venv in Dockerfile |
| 10 | Instruction sufficiency FAIL ingest (`entire-report.txt:68-69`) | Disagree (agent error) | `cli-contract.md:11`; `instruction.md:3` |
| 11 | Non-milestone uses milestone rubric format (user) | Disagree | Single `# Rubric` block only — correct flat format |
| 12 | LLMaJ behavior_in_* PASS | Agree | `entire-report.txt:72-82` verified in section 5 |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | ~215 words, 3 blocks | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer incident narrative | `instruction.md:1-5` |
| 3 | CHECK | No excessive markdown | Plain prose | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | Requirements only | `instruction.md` |
| 5 | CHECK | No hints/strategies | WHAT + contract refs | `instruction.md:3` |
| 6 | CHECK | No design-doc tables | None in instruction | `instruction.md` |
| 7 | CHECK | Well specified | Clear goal, absolute paths | `instruction.md:3` |
| 8 | CHECK | Interesting | Real RTCM3/GNSS scenario | domain |
| 9 | UNCHECK | Unique | Cannot verify vs full corpus | — |
| 10 | CHECK | Absolute paths | `/app/bin/rtcmctl`, `/app/docs/`, `/app/state/…` | `instruction.md:3` |
| 11 | CHECK | Task name not in instruction | Absent | `instruction.md` |
| 12 | CHECK | No canary | None | `instruction.md` |
| 13 | CHECK | No web fetch in env | Offline | `environment/` |
| 14 | CHECK | Pip deps pinned == | Lock file pins all | `requirements.lock:1-6` |
| 15 | CHECK | Base digest-pinned | `@sha256:9f841…` both stages | `Dockerfile:1,14` |
| 16 | CHECK | Env self-contained | COPY from environment/ only | `Dockerfile` |
| 17 | CHECK | No solution in env | Decoys intentional | `instruction.md:3` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose mounts OK | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in venv; test.sh no install | `Dockerfile:28-30`, `test.sh:44-47` |
| 21 | CHECK | Oracle passes | Export: 100% (3/3) | `entire-report.txt:24-25` |
| 22 | CHECK | Oracle offline | copy + cargo build | `solution/solve.sh` |
| 23 | CHECK | Oracle reflective | 7 Rust files + rebuild | `solution/solve.sh:39-47` |
| 24 | CHECK | reward.txt path | 0 at start; 0/1 after pytest | `test.sh:3-4,48-52` |
| 25 | CHECK | Same logic oracle/agent | No `/oracle` branch | `tests/` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `test.sh` |
| 27 | CHECK | Tests aligned | Contracts cover all behaviors | section 5 |
| 28 | CHECK | Correctness not format | Reference codec recomputes | `fixture_codec.py` |
| 29 | CHECK | Behavior not implementation | CLI subprocess + DB asserts | `test_outputs.py` |
| 30 | CHECK | No brittle matching | Computed digests/sums | `fixture_codec.py` |
| 31 | CHECK | Informative docstrings | All tests documented | `test_outputs.py`, `test_tb3_hidden.py` |
| 32 | CHECK | ≥3 negative rubric | Three `-3` lines | `entire-report.txt:285-287` |
| 33 | CHECK | Rubric scores valid | ±1,2,3,5 only | `entire-report.txt:278-287` |
| 34 | CHECK | Agent format | 10 one-line criteria | `entire-report.txt:278-287` |
| 35 | CHECK | Rubric ≤40 positive | 25 pts | `entire-report.txt:278-284` |
| 36 | CHECK | Positive language | Fixes phrased positively | `entire-report.txt:278-284` |
| 37 | CHECK | No /tests/ refs | None | rubric lines |
| 38 | CHECK | No metadata refs | None | rubric lines |
| 39 | CHECK | No oracle/NOP refs | None | rubric lines |
| 40 | CHECK | Required files | All present | task root |
| 41 | CHECK | No stray submission files | Standard layout (audit/review are local review artifacts) | task root |
| 42 | CHECK | author fields | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata | Complete | `task.toml` |
| 44 | CHECK | Tags/category match | rust/sql/bash, data-processing | `task.toml:6-12` |
| 45 | CHECK | Difficulty present | `hard` vs platform medium — not failure | `task.toml:6`, `entire-report.txt:14` |
| 46 | UNCHECK | steps/ layout | N/A non-milestone | `task.toml:9` |
| 47 | UNCHECK | solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not in image | No COPY tests/ | `Dockerfile`, `.dockerignore:14` |
| 51 | CHECK | Solution not in env | .dockerignore excludes | `.dockerignore:13` |
| 52 | CHECK | No trivial input cheat | tmp_path DBs; runtime fixtures | `test_tb3_hidden.py:68-81` |
| 53 | CHECK | No unpinned git | None in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤ 80% | `entire-report.txt:19-20` |
| 55 | CHECK | Not unfair | Solvable; contracts shipped | `entire-report.txt:16-24` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement | Test(s) | Status | Proof |
|-------------|---------|--------|-------|
| MSM7 big-endian u32 scaling | `test_decode_valid_capture`, `test_decode_scale_exponent_nonzero`, `test_hidden_scaled_observable_sum` | covered | `instruction.md:3`, `msm7-contract.md` |
| CRC before staging write | `test_decode_crc_failure_leaves_no_partial`, `test_hidden_mid_batch_crc_aborts` | covered | `instruction.md:3` |
| station_key = station_id:mountpoint | `test_stage_station_key_includes_mountpoint`, `test_hidden_dual_mountpoint_counts` | covered | `staging-contract.md` |
| Staging manifest sorted keys digest | `test_stage_writes_staging_manifest`, `test_tb3_manifest_digest_requires_sorted_keys` | covered | `staging-manifest-contract.md` |
| Persist manifest gate + batch atomicity | `test_persist_rejects_*`, `test_tb3_batch_persist_partial_commit_trap` | covered | `instruction.md:3` |
| Wrap-aware u32 gaps | `test_gap_*`, `test_hidden_gap_wrap_u32` | covered | `snapshot-contract.md` |
| Audit chain_digest order | `test_station_chain_digest_order`, `test_hidden_audit_digest_chronological_order` | covered | `station-ledger-contract.md` |
| Export from snapshot only | `test_export_reads_snapshot_not_live_db`, `test_tb3_report_metrics_export_reads_live_sqlite` | covered | `snapshot-contract.md` |
| mutation_seal_digest | `test_export_rejects_stale_seal_digest`, `test_snapshot_and_seal_written` | covered | `mutation-seal-contract.md` |
| ingest full pipeline | `test_ingest_pipeline_end_to_end`, `test_ingest_writes_state_manifest_snapshot_seal` | covered | `cli-contract.md:11` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-12, spec alignment |
| `task.toml` | #42-45, milestone N/A |
| `environment/Dockerfile` | #14-15, #20, #50 |
| `environment/requirements.lock` | #14 |
| `environment/.dockerignore` | #50, #51 |
| `environment/docs/cli-contract.md` | ingest pipeline, #27 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31 |
| `tests/test_tb3_hidden.py` | anti-cheat |
| `solution/solve.sh` | #21-23 |
| `terminus/reviews/rust-rtcm3-station-msm-staging-ledger-repair-entire-report.txt` | agent stats, rubric, LLMaJ |

---

## 7. Validation & agent performance

### Validation

```
Summary: 0 error(s), 3 warning(s), 2 info
WARNING: pinned_dependencies — cosmetic (lock has == pins)
INFO: non-milestone task
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | best model |
| oracle | 100.0% (3/3) | `entire-report.txt:24-25` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | no (informational only) |

**Rubric:** flat non-milestone; 25 positive / 40 cap; 3 negatives.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder renamed; export relocated |
| 1 Instruction | ☑ | Concise, contract-referenced |
| 2 Environment | ☑ | Digest-pinned, offline |
| 3 Oracle | ☑ | Real rebuild; export 100% |
| 4 Verifiers | ☑ | reward.txt, no runtime install |
| 5 Metadata | ☑ | Complete |
| 6 Rubric | ☑ | Flat format; 25 pts |
| 7 Agent evidence | ☑ | Medium tier; solvable |
| 8 Fairness | ☑ | Strong anti-cheat |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The RTCM3 ingest/staging/ledger repair is well scoped — contracts under `/app/docs/` are thorough, the Dockerfile is offline with a pinned Rust base and verifier venv, and the pytest suite (including TB3 traps and hidden fixtures) checks real behavior end to end. Oracle passes cleanly and agent rates (60–100%) look right for medium difficulty. I didn't find any blocking spec gaps. Optional polish: align `task.toml` difficulty to medium and add a short parenthetical in `instruction.md` that `ingest` runs the full decode→stage→persist→ledger/seal/snapshot pipeline per `cli-contract.md`.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| All categories | no | — |

**Error categories (internal):** none
