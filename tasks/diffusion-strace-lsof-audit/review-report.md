# Terminus Review Report: `diffusion-strace-lsof-audit`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt`; not executed locally) |
| **CHECK count** | 42 |
| **UNCHECK count** | 13 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric, Milestones

**Decision (concise):** Milestone structure, digest-pinned offline environment, anti-cheat fixtures, and Hard difficulty calibration (20% worst-model) are solid. Revise for three High blockers: undocumented `descriptor_leak` detail format (`fd_delta=<N>`) vs instruction prose and brittle verifier parsing; M2 `socket_rows` `len==1` conflicting with contract-wide “all non-loopback peers” semantics while `relay_lane.md` already contains two additional peers; portal rubric stops at `# Rubric 3` for a 7-milestone task and references `/tests/`.

**Insights (concise):**

- `test_descriptor_leak_details` failed 4/10 agent runs; oracle and solution emit `fd_delta=$delta` but contracts never show that format (`steps/milestone_3/tests/test_m3.py:28-31`, `environment/docs/audit_contract.md:20`).
- M2 instruction says “exactly one” peer, but `relay_lane.md` already has `198.51.100.42` and `2001:db8::5` connects (`steps/milestone_2/tests/test_m2.py:51`, `environment/docs/q3_bundles/relay_lane.md:9-12`).
- Per-milestone instructions are each 2–3 paragraphs; automated #1/#4/#31 failures from `terminus review` are false positives for milestone layout.
- Rubric blocks 1–3 are well-formed (≥3 negatives each) but blocks 4–7 are missing; Rubric 3 line references `/tests/` (`entire-report.txt:684`).
- Agent failures are mostly spec-ambiguity (fd_delta string, early full peer parsing), not missing core parsing logic.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #30, #55 | `descriptor_leak` `violations[].detail` format is untested in contracts and mismatches instruction prose. M3 says “with `fd_delta` `5`” (value only). `audit_contract.md` documents bare-path format for `write_outside_run_dir` only. Verifier `_fd_delta()` accepts `fd_delta=<N>` or bare integer; `"fd_delta 5"` raises `ValueError`. Oracle uses `fd_delta=$delta`. 4/10 agent failures on `test_descriptor_leak_details`. | `steps/milestone_3/instruction.md:3`; `environment/docs/audit_contract.md:10,20`; `environment/docs/lsof_contract.md:20-21`; `steps/milestone_3/tests/test_m3.py:28-31,54`; `steps/milestone_3/solution/oracle/StepD.kt:42`; `entire-report.txt:43,56,105-106` | Add explicit example to `audit_contract.md` and M3/M4 instructions, e.g. `detail: "fd_delta=5"`. Optionally relax `_fd_delta()` to accept space-separated forms. |
| 2 | High | Test Alignment/Coverage Issues, Milestones, Instruction Styling | #27, #49, #55 | M2 enforces `len(socket_rows)==1` with only `93.184.216.34:443`, but `strace_contract.md` / `audit_contract.md` define `socket_rows` as all non-loopback peers from all runbooks. `relay_lane.md` already contains two additional non-loopback peers agents parse when following contracts. 3/10 failures on M2 `test_socket_rows`. | `steps/milestone_2/instruction.md:3`; `steps/milestone_2/tests/test_m2.py:47-51`; `environment/docs/strace_contract.md:25-27`; `environment/docs/audit_contract.md:9,17`; `environment/docs/q3_bundles/relay_lane.md:9,12`; `entire-report.txt:33,111-112` | Clarify M2 scope in instruction/contract (e.g. mirror-lane peer only until M6) **or** change M2 test to membership without `len==1` **or** defer relay-lane peer parsing until M6 in contract. |
| 3 | High | Rubric | #32–#39 | Portal rubric has only `# Rubric 1`–`# Rubric 3` for a 7-milestone task. Missing `# Rubric 4`–`# Rubric 7` for audit completion, edge-case parser, cleanup, and verification milestones. Rubric 3 also references `/tests/` (forbidden). | `entire-report.txt:659-685`; `docs/guidelines/rubrics.md:49-58,76` | Add Rubric 4–7 blocks (10–40 pts each, ≥1 negative per block). Remove `/tests/` reference from Rubric 3. |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `descriptor_leak` detail format under-specified; tests accept `fd_delta=5` or bare int; agents used `"fd_delta 5"` and failed M3/M4 (ChatGPT) | **Agree** | `audit_contract.md:20` omits `descriptor_leak` detail example; M3 instruction uses value prose not format (`steps/milestone_3/instruction.md:3`); `_fd_delta()` at `test_m3.py:28-31`; oracle `StepD.kt:42`; 4/10 failures `entire-report.txt:43,56` |
| 2 | M2 socket-row scope mismatch: instruction expects one peer; contract implies all non-loopback; M6 adds relay peers (ChatGPT) | **Partially agree** | M2 instruction **does** say “exactly one” (`steps/milestone_2/instruction.md:3`); conflict is with `strace_contract.md:25-27` + pre-existing `relay_lane.md` peers, not missing M2 text. 7/10 pass `entire-report.txt:33` |
| 3 | Portal rubric incomplete for 7-milestone task; only Rubric 1–3 (ChatGPT) | **Agree** | `entire-report.txt:659-685`; `task.toml:11` (`number_of_milestones = 7`); no `rubric.txt` in task folder |
| 4 | `source_path` absolute vs bare filename ambiguous (entire-report Pattern B) | **Partially agree** | `index_contract.md:9,16` says “relative to bundles root”; test expects `path.name` (`test_m1.py:17,58,140`); 8/10 pass `entire-report.txt:28`. Low severity; add filename example e.g. `burst_lane.md` |
| 5 | `test_audit_responds_to_input_change` behavior not in M4 instruction (entire-report Pattern D) | **Partially agree** | Test injects openat at `test_m4.py:116-135`; M4 instruction lists openat write violations but not dynamic mutation; 7/10 pass. Medium fairness note, not primary blocker |
| 6 | LLMaJ `behavior_in_tests` PASS contradicts fd_delta gap (entire-report:166) | **Partially agree** | Tests cover behavioral thresholds but enforce undocumented string format; LLMaJ overstates “fd_delta=5” as specified in instruction |
| 7 | Automated review blockers #1 concise, #4 step-by-step, #31 docstrings (terminus review) | **Disagree** | Each milestone instruction is 2–3 paragraphs (`steps/milestone_*/instruction.md`); probe rebuild/run lines are standard milestone mechanics; all 63 `test_*` methods have one-line docstrings (e.g. `test_m2.py:29-80`) |
| 8 | Non-canonical base image warning (entire-report:199-224) | **Partially agree** | `environment/Dockerfile:3` uses digest-pinned `python:3.13-slim-bookworm`; tmux/asciinema present (`Dockerfile:10-11`). Prefer canonical t-bench base but digest pin satisfies Edition 2 non-negotiables |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Each of 7 milestone instructions is 2–3 short paragraphs | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Incident-style prose with measurable outputs | `steps/milestone_1/instruction.md:1-4` |
| 3 | CHECK | No excessive markdown formatting | No heavy headers/tables in milestone instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step by step instructions telling the agent what developer steps to take | Rebuild/probe lines are task I/O mechanics, not implementation walkthrough | `steps/milestone_2/instruction.md:3` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | Requirements name outputs/contracts; parsing HOW left to agent | `steps/milestone_3/instruction.md:1-5` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | Tables only in `/app/docs/*_contract.md` env specs | `steps/milestone_*/instruction.md` |
| 7 | UNCHECK | Instruction is well specified (goal is clear and obvious) | fd_delta detail format and M2 peer scope ambiguous vs verifiers | Blockers #1–2 |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Realistic trace-audit / reproducibility workflow | `task.toml:7-8` |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Kotlin strace/lsof runbook audit with 7 milestones | `task.toml:16-17` |
| 10 | CHECK | All paths in instruction are absolute (not relative) | `/app/...` paths throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in milestone instructions | `steps/milestone_*/instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | — |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | Gradle fetch at build time only; no runtime fetch in env code | `environment/Dockerfile:17-23` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `pytest==8.4.1` | `environment/Dockerfile:26` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:3` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY limited to `environment/` subtree | `environment/Dockerfile:33-45` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | `solution/` and `tests/` in `.dockerignore` | `environment/.dockerignore:16-17` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | pytest in image; milestone `test.sh` only runs pytest | `environment/Dockerfile:25-26`, `steps/milestone_1/tests/test.sh:10` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Report: oracle 100% (3/3) | `entire-report.txt:11` |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve scripts copy Kotlin + local gradle build | `steps/milestone_1/solution/solve1.sh:1-9` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | Oracle stages Kotlin sources, builds JAR, runs probes | `steps/milestone_3/solution/solve3.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `steps/milestone_1/tests/test.sh:3,12-16` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `steps/milestone_*/tests/test.sh` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | 0/1 reward only | `steps/milestone_1/tests/test.sh:12-16` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | fd_delta string format; M2 peer count vs contract scope | Blockers #1–2 |
| 28 | CHECK | Tests check for correctness, not just format | Schema counts, peer addresses, violation kinds, runbook content | `steps/milestone_4/tests/test_m4.py:49-89` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | JSON/runbook output assertions; no source grep | `steps/milestone_*/tests/test_m*.py` |
| 30 | UNCHECK | No brittle exact string matching where flexible checks would work | `_fd_delta()` rejects reasonable `fd_delta 5` spacing | `test_m3.py:28-31` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` methods have one-line docstrings | `steps/milestone_*/tests/test_m*.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | Only 3 rubric blocks for 7 milestones; incomplete coverage | `entire-report.txt:659-685` |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | Cannot verify missing Rubric 4–7 | `entire-report.txt:659-685` |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | Missing milestone rubric blocks | `entire-report.txt:659-685` |
| 35 | UNCHECK | Rubric criteria are detailed and precise | M4–M7 milestones lack rubric criteria | `entire-report.txt:659-685` |
| 36 | UNCHECK | Rubric criteria use positive language | Incomplete rubric set | `entire-report.txt:659-685` |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | Rubric 3: “Agent edits tests/ or solution/…” | `entire-report.txt:684` |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | Incomplete rubric; cannot fully verify | `entire-report.txt:659-685` |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | Incomplete rubric; cannot fully verify | `entire-report.txt:659-685` |
| 40 | CHECK | All required files present | Milestone layout: `task.toml`, `environment/Dockerfile`, 7× `steps/milestone_N/` | `task.toml`, `steps/` |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | `diffusion-strace-lsof-audit/` |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, 7 steps | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | kotlin/security/strace/lsof match content | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model 20% | `task.toml:6`, `entire-report.txt:6-7` |
| 46 | CHECK | steps/ layout present with per-milestone files | 7 milestones under `steps/` | `task.toml:27-87` |
| 47 | CHECK | Each milestone has a corresponding solveN.sh file | `solve1.sh`–`solve7.sh` present | `steps/milestone_*/solution/solveN.sh` |
| 48 | CHECK | Each milestone has a corresponding test_mN.py file | `test_m1.py`–`test_m7.py` | `steps/milestone_*/tests/` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | M2 test enforces global peer count inconsistent with later milestones/contracts | `test_m2.py:51`, `test_m6.py:54-62` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile`, `.dockerignore:17` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | solution/tests excluded from image | `environment/.dockerignore:16-17` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Autouse fixtures rebuild from JAR; M4/M6 mutation anti-cheat | `test_m2.py:16-20`, `test_m4.py:116-139` |
| 53 | CHECK | Git repos pinned to specific commit (no unpinned git clone) | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 20% | `entire-report.txt:6-7` |
| 55 | UNCHECK | Task is not too hard or unfair | Systematic spec gaps (fd_delta format, M2 peer trap) caused 68% avg milestone pass with correct logic | `entire-report.txt:99,105-112,139` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 31, 40, 41, 42, 43, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 27, 30, 32, 33, 34, 35, 36, 37, 38, 39, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M3: `descriptor_leak` on burst_lane with fd_delta 5 | `test_descriptor_leak_details` | **gap** | Instruction names value not format (`milestone_3/instruction.md:3`); test requires `fd_delta=5` or `5` (`test_m3.py:28-31,54`) |
| M3: no leak on warmup_lane at threshold | `test_warmup_near_threshold_no_leak` | covered | `test_m3.py:57-65` |
| M3: three out-of-run write paths | `test_lsof_write_outside_*`, `test_spill_bin_outside_run_dir` | covered | `test_m3.py:67-83` |
| M2: exactly one non-loopback peer in socket_rows | `test_socket_rows` | **gap** vs contract | Instruction explicit (`milestone_2/instruction.md:3`); conflicts with `strace_contract.md:25-27` and relay peers |
| M2: loopback excluded | `test_loopback_excluded_from_socket_rows` | covered | `test_m2.py:53-64` |
| M2: three openat write_outside_run_dir paths | `test_openat_outside_run_dir` | covered | `test_m2.py:66-77` |
| M4: violation_count 9, four kinds, dedup | `test_violation_count`, `test_violation_kinds`, `test_violation_dedup` | covered | `test_m4.py:49-69` |
| M4: write_outside_run_dir bare paths | `test_out_of_run_writes` | covered | `test_m4.py:83-89` |
| M4: dynamic response to new openat path | `test_audit_responds_to_input_change` | **partial** | Test exists (`test_m4.py:116-135`); not stated in M4 instruction |
| M1: source_path relative to bundles root | `test_source_paths_populated` | covered (minor ambiguity) | `index_contract.md:9`; test uses filenames (`test_m1.py:140`) |
| M6: relay hex/IPv6/deleted/reversed peers | `test_hex_port_peer`, `test_ipv6_*`, `test_deleted_*`, `test_reversed_*` | covered | `test_m6.py:54-148` |
| M5: four runbook repairs + cleanup schema | `test_seeded_replay_doc`, `test_offline_mirror_doc`, etc. | covered | `test_m5.py:37-82` |
| M7: verification_report fields + relay repairs | `test_verification_schema`, `test_relay_*` | covered | `test_m7.py:37-81` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `steps/milestone_2/instruction.md` | Blocker #2, #49, claim 2 |
| `steps/milestone_2/tests/test_m2.py` | Blocker #2, #27, #49 |
| `steps/milestone_3/instruction.md` | Blocker #1, claim 1 |
| `steps/milestone_3/tests/test_m3.py` | Blocker #1, #27, #30 |
| `steps/milestone_3/solution/oracle/StepD.kt` | Blocker #1, #23 |
| `steps/milestone_4/tests/test_m4.py` | Claim 5, spec alignment |
| `environment/docs/audit_contract.md` | Blocker #1, claim 1 |
| `environment/docs/strace_contract.md` | Blocker #2, claim 2 |
| `environment/docs/lsof_contract.md` | Blocker #1 |
| `environment/docs/index_contract.md` | Claim 4 |
| `environment/docs/q3_bundles/relay_lane.md` | Blocker #2 |
| `environment/Dockerfile` | #13–#20, claim 8 |
| `environment/.dockerignore` | #17, #50, #51 |
| `task.toml` | #42–#46, claim 3 |
| `entire-report.txt` | Agent stats, rubric, claims 1–6 |
| `steps/milestone_*/tests/test_m*.py` | #31 |
| `steps/milestone_*/instruction.md` | #1–#6, #10 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate diffusion-strace-lsof-audit/
Summary: 0 error(s), 64 warning(s), 0 info
Task type detected: milestone
Warnings: informative_test_docstrings (false positive — methods have docstrings), 7 milestones >5 best-practice
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% (1/5) | `entire-report.txt:7` |
| terminus-claude-opus-4-8 | 20.0% (1/5) | `entire-report.txt:6` |
| oracle | 100.0% (3/3) | `entire-report.txt:11` |
| nop | 0.0% (0/1) | `entire-report.txt:10` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20.0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task `diffusion-strace-lsof-audit`; 7-milestone Kotlin/security; report matches folder |
| 1 Instruction | ☑ | Per-milestone concise; fd_delta format + M2 scope gaps |
| 2 Environment | ☑ | Digest-pinned; offline; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☑ | Kotlin staging + probe scripts; 100% per report (not run locally) |
| 4 Verifiers | ☑ | Binary rewards; regeneration fixtures; spec gaps on fd_delta/M2 |
| 5 Metadata | ☑ | `task.toml` complete; hard difficulty calibrated |
| 6 Rubric | ☑ | Only Rubric 1–3 in portal; `/tests/` reference; missing 4–7 |
| 7 LLMaJ & agent evidence | ☑ | fd_delta dominant failure mode; 68.4% avg milestone pass |
| 8 Novelty & fairness | ☑ | Multi-step reasoning; unfair string/count traps |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, digest-pinned Dockerfile, offline Gradle/Kotlin setup, anti-cheat fixtures, and Hard difficulty calibration look solid. Fix three blockers before resubmit: (1) document `descriptor_leak` detail as `fd_delta=<N>` in `audit_contract.md` and M3/M4 instructions — agents reasonably emitted `fd_delta 5` from prose and failed 4/10 runs; (2) resolve M2 `socket_rows len==1` vs contract-wide all-non-loopback-peer semantics while `relay_lane.md` already has extra peers; (3) add portal Rubric 4–7 for the remaining milestones and remove the `/tests/` reference in Rubric 3.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Rubric | yes | 3 |
| Milestones | yes | 2 |
| Metadata Issues | no | — |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Pinning Issues | no | — |
| Task Difficulty | no | — |
