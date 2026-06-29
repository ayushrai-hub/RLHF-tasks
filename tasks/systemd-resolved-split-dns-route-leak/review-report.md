# Terminus Review Report: `systemd-resolved-split-dns-route-leak`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 33 |
| **UNCHECK count** | 22 |

**Error categories (internal):** Rubric, Test Alignment/Coverage Issues, Test Build Issues

**Decision (concise):** Strong Ruby split-DNS debugging task with solid cross-path/digest checks and a sanctioned digest-pinned base, but three High gaps block acceptance: the platform rubric is still for an unrelated bash replay task (mk_contract/gate_host/out_k9.json); verifiers trust the app’s own `internal_leak_count` instead of independently parsing `.rt` slice bytes for qclass=2/scope=1 leaks; and `tests/test.sh` omits canonical `mkdir -p /logs/verifier`. Canonical Ruby base is approved — not an Environment blocker.

**Insights (concise):**

- Platform rubric (entire-report.txt:406–419) references mk_contract.md, gate_host.sh, run_mk.sh, /app/output/out_k9.json — none exist in this task; flat format (no `# Rubric N` headers) is correct for non-milestone, but content is entirely wrong task.
- `ruby:3.3-slim-bookworm@sha256:e76733e…` digest matches sanctioned list in `docs/guidelines/dockerfxile.md:15` — ChatGPT/Harbor canonical-base warning is not a blocker.
- Leak assertions in `tests/test_outputs.py:120–122` read JSON `internal_leak_count` populated by agent-modifiable `count_leaks` in `run.rb:100–102`; no test parses binary rows per `slice_layout.md:19–22`.
- All eight `test_m*` functions have per-test docstrings (`tests/test_outputs.py:75–134`); only module-level docstring is missing (validate warning, not High).
- Agent stats: worst-model 60% (medium tier), 2/10 timeouts — within gate; session-scoped fixture is optional polish, not a blocker.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Rubric | #32–39 | Platform rubric is for a different task (bash replay / mk_contract), not this Ruby split-DNS route-leak task | `entire-report.txt:406–419` cites mk_contract.md, gate_host.sh, write_host.sh, split_host.sh, run_mk.sh, /app/output/out_k9.json; task has merge_k2.rb, evict_p5.rb, fold_m1.rb, emit_h3.rb, /app/output/route_audit.json (`instruction.md:5–12`, `environment/` tree) | Replace platform rubric with flat (non-milestone) criteria for Ruby repair surfaces: merge_k2, evict_p5, fold_m1, emit_h3, route fingerprint binding, leak elimination, anchor preservation, cross-path convergence; ≥3 distinct negatives; 10–40 positive total |
| 2 | High | Test Alignment/Coverage Issues | #27, #28, #51 | Core requirement “no internal query-class rows on external link surfaces” verified only via app-computed `internal_leak_count`; agent can patch `count_leaks` and weaken `validate!` without fixing routing | `tests/test_outputs.py:120–122` asserts JSON field only; `run.rb:100–102` defines `count_leaks`; `engine.rb:48–56` `validate!` also agent-modifiable; `slice_layout.md:19–22` documents qclass/scope offsets but no test parses `.rt` bytes | Add independent slice parser in tests: for each `canonical_path`, count rows with `qclass_code=2` and `scope_code=1` per slice_layout.md; assert independent count == 0 alongside JSON field |
| 3 | High | Test Build Issues | #24 | `test.sh` missing canonical `mkdir -p /logs/verifier` before CTRF/reward writes | `tests/test.sh:1–15` writes `/logs/verifier/ctrf.json` and `/logs/verifier/reward.txt` with no mkdir; canonical template at `docs/guidelines/writing-tests.md:11` | Add `mkdir -p /logs/verifier` (prefer `set -uo pipefail` per template) |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Platform rubric still for wrong task (mk_contract, gate_host, out_k9.json) (ChatGPT) | **Agree** | `entire-report.txt:406–419` vs task files: no mk_contract.md or gate_host.sh; task uses `pact_r4.md`, `route_audit.json` |
| 2 | Verifier trusts `internal_leak_count` instead of parsing `.rt` slice bytes (ChatGPT / test-quality review) | **Agree** | `tests/test_outputs.py:120–122`; `run.rb:100–102`; no `struct` parse of qclass/scope in tests; `entire-report.txt:289–327` |
| 3 | Ruby base not canonical / needs justification (ChatGPT / Harbor review #1) | **Disagree** | `environment/Dockerfile:1` digest `sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df` matches sanctioned `ruby:3.3-slim-bookworm` in `docs/guidelines/dockerfxile.md:15` |
| 4 | Repeated `_build_and_check()` causes timeouts; session fixture needed (ChatGPT / Harbor #2) | **Partially agree** | `tests/test_outputs.py:76–143` calls `_build_and_check()` per test (8×); `entire-report.txt:31` shows 2/10 timeouts (<5 gate) — optimization advisable, not High blocker |
| 5 | `test.sh` should add `mkdir -p /logs/verifier` (ChatGPT Low) | **Agree** (High per Terminus canonical template) | `tests/test.sh:9–14`; `docs/guidelines/writing-tests.md:11` |
| 6 | Assert `band_class <= 1` for every recovered profile, not only run_d (ChatGPT optional) | **Partially agree** | `tests/test_outputs.py:129` checks run_d only; `engine.rb:55` enforces in-app but agent-modifiable — Low polish, not standalone blocker |
| 7 | Non-milestone task uses milestone rubric format (`# Rubric N` blocks) (user query) | **Disagree** | `entire-report.txt:406–419` is flat `Agent …, ±N` list with no `# Rubric 1/2` headers; issue is wrong-task content, not milestone structure |
| 8 | Instruction/spec sufficient; failures are agent exploration timeouts (entire-report LLMaJ) | **Agree** | `entire-report.txt:44–91`; `instruction.md` + `pact_r4.md` cover all test_m1–m8 behaviors per LLMaJ pass at `entire-report.txt:94–95` |
| 9 | Rubric positive total >40 (automated script) | **Disagree as blocker** | Wrong rubric sums to 30 (`./scripts/terminus rubric-points entire-report.txt`); cap irrelevant until correct rubric is authored |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | ~334 words, 3 `##` sections + code block exceeds concise bar | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer tone; contract deferred to pact docs | `instruction.md:1–5` |
| 3 | UNCHECK | No excessive markdown formatting | 3 `##` headers + fenced code block | `instruction.md:7–12` |
| 4 | CHECK | No step by step instructions | Describes outcome, not edit sequence | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Points to contract docs, no bug locations | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, paths, schema fields, held-out arms | `instruction.md:14–28` |
| 8 | CHECK | Instruction is interesting | Real split-DNS / resolver debugging scenario | `instruction.md:1–3` |
| 9 | CHECK | Instruction is unique | Ruby adversarial-generalization split-DNS variant | `task.toml:8`, `reference_pattern` |
| 10 | CHECK | All paths absolute | `/app/environment/...`, `/app/output/route_audit.json` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | Title is "Split DNS route leak" not folder slug | `instruction.md:1` |
| 12 | CHECK | No canary string | No canary patterns | `instruction.md` |
| 13 | CHECK | No web content fetch in env | Local fixtures only | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:15–17` |
| 15 | CHECK | Base image digest-pinned | `@sha256:e76733e…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context stays in environment/ | `COPY . /app/environment` only | `environment/Dockerfile:19` |
| 17 | CHECK | No ground truth in env | fixtures/blk differ from live profiles per LLMaJ | `entire-report.txt:97` |
| 18 | CHECK | No privileged/dangerous Docker ops | Standard RUN/COPY | `environment/Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | `task.toml` |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:15–17`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed in this review (Harbor unavailable/timeout) | — |
| 22 | CHECK | Oracle no internet | Patches + local rebuild only | `solution/solve.sh:10–20` |
| 23 | CHECK | Oracle reflective of instruction | Four patches to Ruby sources, rebuild, checker | `solution/solve.sh`, `solution/*.patch` |
| 24 | UNCHECK | test.sh reward.txt + mkdir | Missing `mkdir -p /logs/verifier` | `tests/test.sh:9–14` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards 0/1 | echo 0/1 to reward.txt | `tests/test.sh:11–14` |
| 27 | UNCHECK | Tests aligned with instructions | Leak requirement not independently verified on slice bytes | Blocker 2 |
| 28 | UNCHECK | Tests check correctness not format | Leak correctness delegated to app counter | Blocker 2 |
| 29 | CHECK | Behavior not implementation grep | End-to-end matrix checker + digest bind | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact strings | Structural/digest checks | `tests/test_outputs.py` |
| 31 | CHECK | Informative test names/docstrings | All 8 tests named test_m* with docstrings | `tests/test_outputs.py:74–134` |
| 32 | UNCHECK | ≥3 negative rubric criteria | Rubric is for wrong task — cannot accept for this submission | `entire-report.txt:406–419` |
| 33 | UNCHECK | Rubric scores ±1,2,3,5 | Wrong-task rubric must be replaced | `entire-report.txt:406–419` |
| 34 | UNCHECK | Rubric Agent format | Wrong-task rubric must be replaced | `entire-report.txt:406–419` |
| 35 | UNCHECK | Rubric detailed and precise | Criteria reference mk_contract/gate_host, not merge_k2/fold_m1 | `entire-report.txt:406–419` |
| 36 | UNCHECK | Rubric positive language | Wrong-task rubric must be replaced | `entire-report.txt:406–419` |
| 37 | UNCHECK | Rubric no /tests/ refs | Wrong-task rubric must be replaced | `entire-report.txt:406–419` |
| 38 | UNCHECK | Rubric no task.toml/instruction refs | Wrong-task rubric must be replaced | `entire-report.txt:406–419` |
| 39 | UNCHECK | Rubric no oracle/NOP mentions | Wrong-task rubric must be replaced | `entire-report.txt:406–419` |
| 40 | CHECK | Required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README | task root |
| 42 | CHECK | author_name/email present | anonymous fields | `task.toml:4–5` |
| 43 | CHECK | Other metadata present | timeouts, category, tags | `task.toml` |
| 44 | CHECK | Tags/languages/category applicable | ruby, dns, system-administration | `task.toml:7–12` |
| 45 | CHECK | Difficulty field present | declared hard; platform medium; not a blocker | `task.toml:6`, `entire-report.txt:16–22` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | Milestone solveN.sh | N/A | `task.toml:11` |
| 48 | UNCHECK | Milestone test_mN.py | N/A (test_m* names are regular test IDs, not milestone files) | `task.toml:11` |
| 49 | UNCHECK | Milestone scope isolation | N/A | `task.toml:11` |
| 50 | CHECK | Tests not baked into image | No COPY tests/ | `environment/Dockerfile:19` |
| 51 | UNCHECK | Solution not accessible in env | Leak counter hack path via run.rb/engine.rb | Blocker 2 |
| 52 | CHECK | Agent cannot trivially modify inputs | `_reset_var()` wipes var/ each test | `tests/test_outputs.py:26–32,44` |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80%) | Worst-model 60% | `entire-report.txt:21–22` |
| 55 | CHECK | Not too hard/unfair | Solvable; spec sufficient per LLMaJ | `entire-report.txt:18,44–91` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 25, 26, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 52, 53, 54, 55 |
| **UNCHECK** | 1, 3, 21, 24, 27, 28, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49, 51 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| var_check exits 0; 8 matrix rows | test_m1_harness_exit_clean | covered | `tests/test_outputs.py:74–78` |
| route_fingerprint = sha256(slice bytes) | test_m2_byte_bind_stable | covered | `tests/test_outputs.py:81–87` |
| run_a/run_b cross-path + zero leaks | test_m3_public_smoke_guard | gap (leak via JSON only) | `tests/test_outputs.py:90–96` |
| run_c held-out VPN reorder cross-path | test_m4_slot_obligations | covered | `tests/test_outputs.py:99–103` |
| All profiles uninterrupted vs recovered agree | test_m5_dual_path_rows | covered | `tests/test_outputs.py:106–111` |
| q9 interim rows insufficient; zero leaks | test_m6_interim_row_trap | gap (leak via JSON only) | `tests/test_outputs.py:114–122` |
| run_d band_class ≤ 1; cross-path | test_m7_second_pass_guard | covered (band partial) | `tests/test_outputs.py:125–130` |
| lane.epoch anchor preserved | test_m8_anchor_preserve_guard | covered | `tests/test_outputs.py:133–142` |
| No internal qclass rows on external surfaces | — | **gap** | Instruction `instruction.md:22`; no binary slice leak parse in tests |
| band_class ≤ 1 on every recovered row (pact) | test_m7 only run_d | partial | `environment/docs/pact_r4.md`; `tests/test_outputs.py:129` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #3, #7, spec alignment |
| `task.toml` | #45, #46–49 N/A |
| `environment/Dockerfile` | #15, #20, canonical base adjudication |
| `environment/cmd/var_daemon/run.rb` | Blocker 2, claim 2 |
| `environment/cmd/var_check/engine.rb` | Blocker 2, claim 2 |
| `environment/docs/slice_layout.md` | Blocker 2, independent leak parse spec |
| `tests/test.sh` | Blocker 3, #24 |
| `tests/test_outputs.py` | Blocker 2, #27–28, #31 |
| `entire-report.txt` | Rubric, agent stats, external adjudication |
| `docs/guidelines/dockerfxile.md` | Canonical base adjudication |
| `solution/solve.sh` | #22–23 |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate systemd-resolved-split-dns-route-leak/
Summary: 0 error(s), 9 warning(s), 1 info
Task type detected: regular
Warnings: missing module-level docstring in test_outputs.py (all test functions have docstrings)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100.0% (5/5) | best model |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 2 timeouts |
| oracle | 100.0% (3/3) | per platform report |
| nop | 0.0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular task; report matches folder; `number_of_milestones = 0` |
| 1 Instruction | ☑ | Well specified; ## headers borderline (#1, #3 Medium) |
| 2 Environment | ☑ | Digest matches sanctioned Ruby base; tmux/asciinema present |
| 3 Oracle | ☐ | Not executed locally; static review passes #22–23 |
| 4 Verifiers | ☑ | Blockers: mkdir, independent leak parse |
| 5 Metadata | ☑ | Complete; difficulty mismatch informational |
| 6 Rubric | ☑ | Wrong-task rubric — flat format OK, content not |
| 7 LLMaJ & agent evidence | ☑ | 60% worst-model; spec sufficient |
| 8 Novelty & fairness | ☑ | Multi-module Ruby fix; held-out profiles |
| 9 Long context | — | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Ruby split-DNS task — the held-out profile arms, byte-level fingerprint binding, and cross-path convergence checks are well thought out, and the digest-pinned Ruby base is on the approved list. Three things to fix before accept: (1) replace the platform rubric — it still describes an unrelated bash replay task (mk_contract, gate_host, out_k9.json) instead of merge_k2/evict_p5/fold_m1/emit_h3 and route_audit convergence; (2) add an independent leak check that parses each canonical `.rt` slice for qclass=2 + scope=1 rows per slice_layout.md, not just the JSON `internal_leak_count` field the agent can zero out in run.rb; (3) add `mkdir -p /logs/verifier` to tests/test.sh. Optional polish: session-scoped build fixture to cut verifier runtime.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Rubric | yes | 1 |
| Test Alignment/Coverage Issues | yes | 2 |
| Test Build Issues | yes | 3 |
| Environment | no | — |
| Instruction Styling | no (Medium #1/#3 only) | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
