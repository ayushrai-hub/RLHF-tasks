# Terminus Review Report: `pubsub-delivery-validator-go`

**Generated:** 2026-07-09 17:30 UTC  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/pubsub-delivery-validator-go`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** none

**Decision (concise):** Accept. This is a well-built Go debugging task with digest-pinned canonical base image, offline verifier setup, instruction coverage of all core boundary rules, and 49 independent reference-style tests. ChatGPT’s Accept recommendation holds after artifact review. The Harbor export’s “non-canonical base image” Revise call is incorrect per `docs/guidelines/dockerfile.md`. Automated audit false-positives on pip pinning (#14) and phantom test thresholds (#27). Rubric uses correct non-milestone flat format at 25/40 positive points.

**Insights (concise):**

- `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452…` is listed as a canonical base in `docs/guidelines/dockerfile.md` — external Harbor report recommendation to switch to `ghcr.io/laude-institute/t-bench/*` does not apply.
- Platform rubric is a flat `Agent …, ±N` list (no `# Rubric 2+` headers) with 25 positive points and 3 negatives — correct non-milestone format, not milestone-block layout.
- Worst-model pass rate 20% (GPT-5.5) aligns with declared `hard` tier; Claude Opus 100% does not block.
- Minor spec gaps: `priority_distribution` bucket labels (high≥3, medium=2, low<2) live in source/`priority_scoring.md` but not `instruction.md`; acceptable for a code-debugging task where reading implementation is expected.
- `instruction.md` uses `./cmd/pubsub-validator` after `cd /app` — only relative token; not a substantive blocker.
- `category = "system-administration"` should be `debugging` per taxonomy — cosmetic metadata note only.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept — no High/Medium blockers | Agree | Dockerfile digest-pinned; `allow_internet = false` (`task.toml:17`); pip pinned `pytest==8.4.1` (`environment/Dockerfile:12-13`); tests recompute from raw data (`tests/test_outputs.py:29-254`); oracle 100% (`entire-report.txt:26`) |
| 2 | ChatGPT: Dockerfile digest-pinned, offline setup | Agree | `environment/Dockerfile:1` `@sha256:1a6d4452…`; `tests/test.sh` has no apt/pip/curl installs |
| 3 | ChatGPT: Rubric positive total within cap | Agree | `./scripts/terminus rubric-points entire-report.txt` → 25/40; 11 `+N` lines, 3 negatives (`entire-report.txt:349-362`) |
| 4 | ChatGPT: Generic directory name cosmetic only | Agree | Folder is `pubsub-delivery-validator-go`; no functional impact |
| 5 | Harbor export: Non-canonical base image → Revise | **Disagree** | `docs/guidelines/dockerfile.md:11` lists exact image+digest as canonical; task matches |
| 6 | Harbor export: Misleading comment density may skew difficulty | Partially agree | Intentional per `instruction.md:1` (“Code comments and documentation files may contain errors”); design choice, not blocker |
| 7 | Instruction sufficiency: priority bucket thresholds undefined | Partially agree | `high_priority_violations` threshold `>=3` in `environment/docs/priority_scoring.md:20` and `pkg/priority/priority.go:58,84-90`; `priority_distribution` buckets only in source — not in `instruction.md`. Medium note only; agents failed by guessing `>=4`, not missing core algorithm spec |
| 8 | Instruction sufficiency: throttle `peak_rate` / ceiling trap | Partially agree | `instruction.md:5` specifies floor division for bucket size; `test_throttle_peak_rate` docstring defines formula (`tests/test_outputs.py:611`); `_compute_throttle()` uses floor (`tests/test_outputs.py:238-250`). Ceiling bug fails `test_throttle_peak_rate` even if `throttle_events` coincidentally match |
| 9 | LLMaJ: behavior_in_task_description PASS | Agree | Instruction covers unsub half-open, per-client dup, strict ordering, float latency, DL `>=`, retention `>`, priority weights/normalization, backpressure, throttle floor, fanout, output path (`instruction.md:1-7`) |
| 10 | LLMaJ: behavior_in_tests PASS | Agree | 49 `test_*` functions with independent `_compute_*` helpers mirror instruction semantics |
| 11 | Test quality review: ACCEPT | Agree | Reference implementations in Python; cross-module consistency tests present |
| 12 | Auto-audit #10: relative paths in instruction | Partially agree | Only `./cmd/pubsub-validator` in build command (`instruction.md:1`); preceded by `cd /app`. Technically relative; not material |
| 13 | Auto-audit #14: unpinned pip | **Disagree** | `pytest==8.4.1` and `pytest-json-ctrf==0.3.5` pinned (`environment/Dockerfile:12-13`) |
| 14 | Auto-audit #27: phantom thresholds 8, 45, 500000 | **Disagree** | `500000` = 500KB binary min (`instruction.md:7`, `tests/test_outputs.py:265`); `45` = fixture delivery count (`tests/test_outputs.py:293`); `8` = anti-gut line minimum (`tests/test_outputs.py:737`) |
| 15 | Auto-audit #44: category mismatch | Agree | `task.toml:6` `system-administration`; primary activity is bug-fixing → should be `debugging` per `docs/task-type-taxonomy.md:15,29`. Single Medium metadata note |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | ~4 prose blocks, ~299 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Human problem statement, no synthetic framing | `instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step solve instructions | States goal and rules, not patch order | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | WHAT not HOW; warns docs may lie | `instruction.md:1` |
| 6 | CHECK | No design-doc I/O tables | No mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Clear output path, build cmd, all core algorithms | `instruction.md:1-7` |
| 8 | CHECK | Interesting | Realistic pub/sub delivery audit scenario | `instruction.md` |
| 9 | UNCHECK | Unique vs corpus | Cannot verify from artifacts alone | — |
| 10 | UNCHECK | Absolute paths only | `./cmd/pubsub-validator` in build command | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No task folder name present | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | No curl/wget in env code | `environment/` |
| 14 | CHECK | Pinned pip dependencies | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:12-13` |
| 15 | CHECK | FROM digest-pinned | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Env context only | COPY limited to `environment/` | `environment/Dockerfile:16-27` |
| 17 | CHECK | No ground-truth answers in env | Misleading comments intentional; instruction warns | `instruction.md:1` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN | `environment/Dockerfile` |
| 19 | CHECK | Compose does not conflict mounts | No compose file | — |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:11-13`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:26` |
| 22 | CHECK | Oracle no internet | solve.sh patches local files only | `solution/solve.sh` |
| 23 | CHECK | Oracle derives answer | 10 targeted source patches + rebuild | `solution/solve.sh:5-167` |
| 24 | CHECK | reward.txt on pass/fail | Canonical block writes 0/1 | `tests/test.sh:28-32` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards 0/1 | `echo 0` / `echo 1` only | `tests/test.sh:28-32` |
| 27 | CHECK | Tests aligned with instructions | All core rules traced; minor schema details in docs/source | `instruction.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check correctness | Independent `_compute_*` vs JSON output | `tests/test_outputs.py:29-254` |
| 29 | CHECK | Behavior not implementation grep | No source grepping for logic | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact-string checks | Numeric tolerances, structural asserts | `tests/test_outputs.py` |
| 31 | CHECK | Informative test docstrings | All `test_*` have docstrings (AST-verified) | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 3 negatives at -1, -2, -3 | `entire-report.txt:360-362` |
| 33 | CHECK | Rubric scores ±1,2,3,5 | All 14 lines valid | `entire-report.txt:349-362` |
| 34 | CHECK | `Agent …, ±N` one-line format | 14 properly formatted lines | `entire-report.txt:349-362` |
| 35 | CHECK | Rubric detailed; positive ≤40 | 25 positive pts (11 lines) | `entire-report.txt:349-359` |
| 36 | CHECK | Positive phrasing in rubric | No “Agent does not …, +N” | `entire-report.txt:349-362` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:349-362` |
| 38 | CHECK | Rubric no task.toml/instruction refs | None | `entire-report.txt:349-362` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:349-362` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No jobs/ or stray README in task dir | task root |
| 42 | CHECK | author_name/email present | Both set | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | version, timeouts, languages, tags | `task.toml` |
| 44 | UNCHECK | Tags/category applicable | `category` should be `debugging` not `system-administration` | `task.toml:6` |
| 45 | CHECK | Difficulty present | `difficulty = "hard"`; worst-model 20% → hard tier | `task.toml:8`, `entire-report.txt:16-22` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:11` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:11` |
| 49 | UNCHECK | Per-milestone test scope | N/A | `task.toml:11` |
| 50 | CHECK | Tests not baked into image | `.dockerignore` excludes `tests/`; no COPY tests | `environment/.dockerignore:11`, `environment/Dockerfile` |
| 51 | CHECK | Solution not in environment | `.dockerignore` excludes `solution/` | `environment/.dockerignore:10` |
| 52 | CHECK | Agent cannot trivially mutate inputs | Fixture at `/app/data/`; correctness requires algorithm | `environment/data/delivery_log.json` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 20% ≤ 80% | `entire-report.txt:21-22` |
| 55 | CHECK | Not unfair / unavailable info | Core rules in instruction; agent failures were implementation bugs at 47-48/49 | `entire-report.txt:83-116` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 10, 44, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Half-open unsub window (`>= unsub_ts` invalid) | `test_unsub_boundary_exclusive`, `test_unsub_violations_count` | covered | `instruction.md:3`; `tests/test_outputs.py:50` |
| Per-client duplicate scoping | `test_duplicate_violations_per_client`, `test_duplicate_not_cross_client` | covered | `instruction.md:3`; `tests/test_outputs.py:55-59` |
| Strictly increasing seq per client+topic | `test_ordering_violations_strict`, `test_ordering_d04_regression` | covered | `instruction.md:3`; `tests/test_outputs.py:67` |
| Float mean interval | `test_latency_float_division`, `test_avg_mean_interval` | covered | `instruction.md:3`; `tests/test_outputs.py:138` |
| Dead letter `retry_count >= max` | `test_deadletter_retry_exhaustion`, `test_deadletter_total` | covered | `instruction.md:3`; `tests/test_outputs.py:91` |
| Retention TTL strict `>`; age stats expired-only | `test_retention_strict_boundary`, `test_retention_age_fields` | covered | `instruction.md:3-4`; `tests/test_outputs.py:118` |
| Priority weights 5/3/3; normalize by total deliveries | `test_priority_normalization` | covered | `instruction.md:5`; `tests/test_outputs.py:146-168` |
| Backpressure float threshold; index 4dp | `test_backpressure_float_threshold` | covered | `instruction.md:5`; `tests/test_outputs.py:186-187` |
| Throttle floor division; buckets >2 | `test_throttle_floor_division` | covered | `instruction.md:5`; `tests/test_outputs.py:238` |
| Throttle peak_rate | `test_throttle_peak_rate` | covered | `_compute_throttle` formula; `tests/test_outputs.py:250,610-620` |
| Fanout ratio 4dp | `test_fanout_ratio` | covered | `instruction.md:5`; `tests/test_outputs.py:634` |
| Output at `/app/output/results.json` | `test_output_schema` | covered | `instruction.md:1`; `tests/test_outputs.py:14` |
| ELF binary >500KB | `test_binary_exists` | covered | `instruction.md:7`; `tests/test_outputs.py:265` |
| Deterministic output | `test_rerun_deterministic` | covered | `instruction.md:7`; `tests/test_outputs.py` |
| Config override must not disable checks | `test_config_override_inactive` | covered | `instruction.md:1`; `tests/test_outputs.py:751-759` |
| `pubsub.toml` authoritative | implied by config override test | covered | `instruction.md:1`; `environment/config/delivery_mode.toml` |
| Priority distribution buckets high/medium/low | `test_priority_distribution` | gap (minor) | Buckets in `pkg/priority/priority.go:84-90`; not in `instruction.md` — acceptable for debugging |
| `high_priority_violations` threshold ≥3 | `test_priority_high_violations` | covered | `environment/docs/priority_scoring.md:20`; `tests/test_outputs.py:163` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10, #11, spec alignment |
| `task.toml` | #42-45, #44 category |
| `environment/Dockerfile` | #14-15, #20, canonical base |
| `environment/.dockerignore` | #50-51 |
| `environment/docs/output_schema.md` | Output field contract |
| `environment/docs/priority_scoring.md` | High-priority threshold |
| `environment/pkg/priority/priority.go` | Distribution buckets |
| `environment/config/delivery_mode.toml` | Config override trap |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #21, #32-39, #45, #54, agent stats |
| `docs/guidelines/dockerfile.md` | Canonical base adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate pubsub-delivery-validator-go/
Summary: 0 error(s), 2 warning(s), 2 info
```

Warnings: relative-path heuristic on instruction; pip line-wrap false positive (packages are pinned).

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | Reference |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | hard |
| Platform classified | hard |
| Tier match (#45) | yes (informational) |

### Rubric (platform, non-milestone)

| Field | Value |
|-------|-------|
| Format | Flat `Agent …, ±N` list — **no** `# Rubric 2+` milestone headers |
| Positive total | 25 (cap 40) |
| Negative count | 3 |
| Status | PASS |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `pubsub-delivery-validator-go`; regular layout; Go debugging task |
| 1 Instruction | ☑ | Concise, well-specified; one `./` in build cmd |
| 2 Environment | ☑ | Canonical digest-pinned Go image; tmux+asciinema; offline |
| 3 Oracle | ☑ | Patches source, rebuilds; 100% pass in report |
| 4 Verifiers | ☑ | 49 tests; independent reference impl; reward.txt canonical |
| 5 Metadata | ☑ | `allow_internet=false`; category should be `debugging` |
| 6 Rubric | ☑ | Flat non-milestone format; 25/40 positives; 3 negatives |
| 7 Agent evidence | ☑ | 20% worst-model = hard; instruction sufficiency gaps minor |
| 8 Novelty & fairness | ☑ | Multi-bug interaction; anti-cheat via recompute + config trap |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The instructions are clear on the core boundary rules, the environment is well set up with a pinned Go base and verifier deps baked into the image, and the tests independently recompute expected results from the raw delivery log — strong coverage across violations, dead-letter, retention, priority, backpressure, throttle, and determinism. Oracle passes cleanly and the 20% worst-model rate fits hard difficulty. I’d suggest relabeling `category` to `debugging` and optionally spelling out priority bucket labels in the instruction, but neither blocks acceptance. The platform rubric is correctly formatted as a flat non-milestone list at 25 positive points.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Time Based Tests | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Milestones | no | — |
| Uses Internet | no | — |
| Agent Timeout | no | — |
| Wrong Coding Language | no | — |
| Canary Strings | no | — |
| Rubric | no | — |
| Test Dependency Location | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| UI | no | — |
| Other | no | — |

---

_Report enriched after manual audit per `prompt.md`. Baseline from `./scripts/terminus validate`, `./scripts/terminus audit`, `./scripts/terminus review`._
