# Terminus Review Report: openssl-totp-gin-suite

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform 3/3; local run blocked — Docker socket) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong C/Go MFA debugging task with excellent anti-cheat (integrity-pinned drivers, independent Python replay, live CLI cross-checks) and appropriate hard difficulty (0–40% agent pass). One real blocker: dual-epoch passcode materialization blending (`lane_blend_epochs` within ±1 step → use host epoch) is enforced by `test_probe_matches_independent_python_derivation` and `test_probe_passcode_tracks_passcode_epoch_binding` but contradicts `http_contract.md` line 86 (“must follow the passcode epoch”). Automated review flags for #13 (localhost HTTP in `step_driver.py`) and #14 (multiline `uv pip install`) are false positives. Platform rubric (in submission report) uses correct **non-milestone** flat format — not milestone blocks.

**Insights (concise):**

- 5/8 agent trials reached 40/41; all five failures trace to probe/epoch-blend semantics (`test_probe_matches_independent_python_derivation` 3/10 pass).
- `lane_blend.c` already contains blend logic; bugs are `lane_sync.c` reading `K9_CLOCK_EPOCH` instead of `K9_PASSCODE_EPOCH` and `host_step_width()` using `step_window` instead of `step_seconds` — blend rule itself must still be documented.
- Oracle 100% (3/3) on platform; solve.sh derives fixes from source repair + rebuild + graded driver.
- Dockerfile digest-pinned; verifier deps baked (`pytest==8.4.1`, `pytest-json-ctrf==0.3.5`); `allow_internet = false`.
- Submission rubric (platform text, `entire-report.txt` L362–374): flat `Agent …, ±N` list, 5 negatives, 24 positive pts — valid for `number_of_milestones = 0`; no `# Rubric 2+` misuse.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Dual-epoch passcode materialization blending is tested but not specified in normative docs. `http_contract.md` says materialization “must follow the passcode epoch” while tests require: when `host_epoch` and `passcode_epoch` differ by at most one `step_seconds` step, materialize at `host_epoch`; otherwise use `passcode_epoch`. | `environment/docs/http_contract.md:86`; `tests/test_outputs.py:126-134` (`_material_epoch`); `tests/test_outputs.py:862-906` (`test_probe_matches_independent_python_derivation` uses `host_epoch=clock_base+30`, `passcode=clock_base` → expects `host_epoch` material); agent stats: 5 trials at 40/41 on this probe test | Add explicit blend rule to `http_contract.md` (and optionally `verifier_seeds.md`) with worked example: e.g. `K9_CLOCK_EPOCH=1700000070`, `K9_PASSCODE_EPOCH=1700000040`, `step_seconds=30` → material epoch `1700000070`. |

*No other High/Medium blockers found after full artifact audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Dual-epoch passcode materialization rule under-specified; verifier expects blended rule (ChatGPT / `entire-report.txt` L101–102, L127, L157) | **Agree** | `http_contract.md:86` vs `test_outputs.py:126-134,890-906`; 5/8 trials at 40/41 on probe epoch tests |
| 2 | Optional: note pytest-json-ctrf preinstalled in test.sh (ChatGPT Low / `entire-report.txt` L262–280) | **Agree** (Low only) | `environment/Dockerfile:21-22`; `tests/test.sh:3` — cosmetic, not a blocker |
| 3 | LLMaJ `behavior_in_task_description` PASS (`entire-report.txt` L162) | **Partially agree** | Instruction points to docs for all tested behavior, but `http_contract.md:86` contradicts probe blend tests |
| 4 | LLMaJ `task_instruction_sufficiency` FAIL (`entire-report.txt` L78, L127–131) | **Agree** | Same epoch-blend gap; systematic 40/41 failures |
| 5 | Automated review READY TO USE (`entire-report.txt` L311–315) | **Disagree** | Epoch-blend spec gap is a revision blocker per `prompt.md` hidden-semantics rule |
| 6 | Instruction brevity / implicit requirements (`entire-report.txt` L204–230) | **Partially agree** (not blocker) | `instruction.md` is 2 paragraphs; normative docs under `/app/environment/docs/` are thorough — acceptable for `difficulty = hard` |
| 7 | Non-canonical Dockerfile base (`entire-report.txt` L234–255) | **Partially agree** (not blocker) | `environment/Dockerfile:1` uses digest-pinned Debian; justified for C+Go+Python toolchain |
| 8 | Automated #13 web fetch in `step_driver.py` (`review_checklist.py`) | **Disagree** | `step_driver.py:33-43` calls `http://127.0.0.1:9477` (local MFA host), not external web |
| 9 | Automated #14 unpinned pip (`validate` / `review_checklist.py`) | **Disagree** | `environment/Dockerfile:21-22` pins `pytest==8.4.1 pytest-json-ctrf==0.3.5`; false positive from multiline `uv pip install` |
| 10 | Non-milestone task wrongly uses milestone rubric format (user query) | **Disagree** | `task.toml:11` `number_of_milestones = 0`; platform rubric (`entire-report.txt` L362–374) is flat `Agent …, ±N` with no `# Rubric 2+` — correct per `docs/guidelines/rubrics.md:60` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Two short paragraphs | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer tone; points to bundled docs | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step-by-step instructions telling the agent what developer steps to take | States outcome, not fix steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies (describes WHAT to build, not HOW) | No named bugs/files | `instruction.md` |
| 6 | CHECK | No design doc style tables mapping inputs to outputs | No tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified (goal is clear and obvious) | Clear deliverable: fix CLI, rebuild, regenerate ledger | `instruction.md` |
| 8 | CHECK | Instruction is interesting (useful to some group of developers) | Real MFA/C integration debugging | — |
| 9 | CHECK | Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task) | Distinct C/Go/OpenSSL TOTP suite | — |
| 10 | CHECK | All paths in instruction are absolute (not relative) | All `/app/...` paths | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No `openssl-totp-gin-suite` string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web (other than packages) | `step_driver.py` HTTP is localhost MFA host only | `step_driver.py:19,33-43` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == (no ranges) | pytest and CTRF plugin pinned | `environment/Dockerfile:21-22` |
| 15 | CHECK | Base Docker image is pinned by digest (@sha256:...) | Digest-pinned FROM | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside the environment directory | COPY only env subdirs | `environment/Dockerfile:31-43` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Buggy sources intentional; docs are contracts not answers | `environment/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | `task.toml` |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages at runtime | Deps in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:19-23`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently (no flaky behavior) | Platform oracle 100% (3/3) | `entire-report.txt` L25 |
| 22 | CHECK | Oracle does not require internet or downloading packages | solve.sh only patches sources + rebuild | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction (real implementation, not hardcoded) | 11 source fixes + `build_m3.sh` + `grad_driver.sh` | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Canonical reward block | `tests/test.sh:10-20` |
| 25 | CHECK | Verifiers use the exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only (0 or 1, no partial scores) | Binary 0/1 | `tests/test.sh:16-19` |
| 27 | UNCHECK | All tests are aligned with instructions (do not test unstated requirements) | Probe blend semantics tested but not in `http_contract.md` | Blocker #1 |
| 28 | CHECK | Tests check for correctness, not just format | Live CLI replay, HOTP cross-check, store persistence | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation (no grepping source code) | Runtime CLI/HTTP assertions | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Status tokens from schema; crypto via derivation | `ledger_schema.md`, `test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | 41 tests with docstrings | `tests/test_outputs.py` |
| 32 | UNCHECK | Rubrics contain at least 3 negative penalty criteria | N/A — no `rubric.txt` in task folder (platform-side) | — |
| 33 | UNCHECK | Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5} | N/A — no local rubric file | — |
| 34 | UNCHECK | Each rubric criterion is one line starting with Agent, comma, then score | N/A — no local rubric file | — |
| 35 | UNCHECK | Rubric criteria are detailed and precise | N/A — no local rubric file | — |
| 36 | UNCHECK | Rubric criteria use positive language | N/A — no local rubric file | — |
| 37 | UNCHECK | Rubric does not reference testing logic or /tests/ directory | N/A — no local rubric file | — |
| 38 | UNCHECK | Rubric does not reference metadata (task.toml) or instruction.md | N/A — no local rubric file | — |
| 39 | UNCHECK | Rubric does not mention oracle or NOP runs | N/A — no local rubric file | — |
| 40 | CHECK | All required files present | instruction, task.toml, Dockerfile, solve.sh, test.sh | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task layout | task root |
| 42 | CHECK | author_name and author_email fields present in task.toml | Present | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, allow_internet | `task.toml` |
| 44 | CHECK | Tags, languages, categories are applicable to the task | security, c, go, openssl, totp, api_integration | `task.toml` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best-model 0%, worst 40% ≤80% | `entire-report.txt` L19-21; `docs/guidelines/difficulty.md` |
| 46 | UNCHECK | steps/ layout present with per-milestone files | N/A — `number_of_milestones = 0` | `task.toml:11` |
| 47 | UNCHECK | Each milestone has a corresponding solveN.sh file | N/A | `task.toml:11` |
| 48 | UNCHECK | Each milestone has a corresponding test_mN.py file | N/A | `task.toml:11` |
| 49 | UNCHECK | Each milestone test file is scoped only to that milestone | N/A | `task.toml:11` |
| 50 | CHECK | Tests are NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution or ground truth answers are not accessible in the environment | No solution/ in image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot modify input data to trivially pass tests | Integrity pins on driver scripts; independent replay | `harness_integrity.md`, `test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (not >80% combined pass rate consistently) | Worst-model 40% | `entire-report.txt` L21 |
| 55 | UNCHECK | Task is not too hard or unfair (not requiring unavailable info) | Undocumented epoch-blend rule causes systematic 40/41 failures | Blocker #1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 27, 32, 33, 34, 35, 36, 37, 38, 39, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Regenerate `/app/output/run_ledger.json` via graded driver | `test_terminal_statuses_match_independent_replay`, `test_graded_driver_scripts_unmodified` | covered | `instruction.md`; `test_outputs.py` |
| Ledger schema statuses and digest/kid rules | `test_ledger_schema`, `test_failure_rows_blank_digest`, `test_ok_rows_lowercase_hex` | covered | `ledger_schema.md`; `test_outputs.py` |
| 23 seeded scenarios all represented | `test_suite_covers_all_seed_names` | covered | `verifier_seeds.json`; `test_outputs.py` |
| Store files mode 0600 | `test_store_permission_mode` | covered | `http_contract.md:116`; `test_outputs.py` |
| No hand-written ledger / pinned scripts | `test_graded_driver_scripts_unmodified` | covered | `harness_integrity.md`; `test_outputs.py` |
| Independent CLI replay matches ledger | `test_terminal_statuses_match_independent_replay` | covered | `test_outputs.py` |
| Passcode derivation cross-check | `test_independent_passcode_matches_host_mfa` | covered | `http_contract.md:86-88`; `test_outputs.py` |
| Probe emits six-digit code | `test_probe_subcommand_emits_six_digit_code` | covered | `http_contract.md:92`; `test_outputs.py` |
| **Dual-epoch blend: within ±1 step use host epoch** | `test_probe_matches_independent_python_derivation`, `test_probe_passcode_tracks_passcode_epoch_binding` | **gap** | `http_contract.md:86` says passcode epoch only; `test_outputs.py:126-134` |
| `K9_PASSCODE_EPOCH` binding (not `K9_CLOCK_EPOCH`) | Implicit in probe/MFA passcode tests | covered in code, partial in docs | `solution/solve.sh:66-80`; `lane_sync.c` bug |
| Stride must not shrink when passcode binding active | Graded scenarios with offset | covered | `http_contract.md:86`; `solution/solve.sh:83-99` |
| Session seal MAC input / verify exit 12 | `test_verify_subcommand_rejects_tampered_token`, seal scenarios | covered | `http_contract.md:96-100`; `test_outputs.py` |
| `clock_offset_steps` host advance, passcode at base | Offset-window scenarios | covered | `verifier_seeds.md:25`; `test_outputs.py` `_replay_scenario` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1–#12, #7 |
| `environment/docs/http_contract.md` | Blocker #1, #27, #55, spec alignment |
| `environment/docs/ledger_schema.md` | Spec alignment |
| `environment/docs/verifier_seeds.md` | Spec alignment |
| `environment/docs/harness_integrity.md` | #52 |
| `tests/test_outputs.py` | Blocker #1, #27–#31, #55 |
| `tests/test.sh` | #20, #24–#26 |
| `environment/Dockerfile` | #13–#20, #50 |
| `environment/pkt_vend/src/lane_blend.c` | Blend implementation (buggy `step_window`) |
| `environment/pkt_vend/src/lane_sync.c` | Buggy env var read |
| `solution/solve.sh` | #21–#23, oracle behavior |
| `task.toml` | #42–#45, #46–#49 |
| `entire-report.txt` | Agent stats, platform rubric, LLMaJ |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: openssl-totp-gin-suite/ ===
Summary: 0 error(s), 2 warning(s), 1 info
- INFO: non-milestone (preferred milestone for new submissions)
- WARN: multiline uv pip install line triggers false unpinned warning (packages are == pinned)
- WARN: missing .dockerignore
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 40.0% (2/5) | Best model |
| terminus-claude-opus-4-8 | 0.0% (0/5) | 1 timeout |
| oracle | 100.0% (3/3) | Platform |
| nop | 0.0% (0/1) | — |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium (worst-model) |
| Declared difficulty | hard |
| Tier match (#45) | yes — best-model 0% supports hard per `difficulty.md` |

**Per-test signal (probe epoch):** `test_probe_matches_independent_python_derivation` 3/10; `test_probe_passcode_tracks_passcode_epoch_binding` 6/10 — confirms systematic spec gap, not random agent noise.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | `openssl-totp-gin-suite`; regular (non-milestone); security/api_integration |
| 1 Instruction | ☑ | Concise; absolute paths; no hints |
| 2 Environment | ☑ | Digest-pinned; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☑ | Source-derive; platform 100% |
| 4 Verifiers | ☑ | Canonical test.sh; 41 behavior tests; epoch-blend gap |
| 5 Metadata | ☑ | `allow_internet=false`; timeouts plausible |
| 6 Rubric | ☑ | Platform rubric flat format OK for non-milestone; no local file |
| 7 LLMaJ & agent evidence | ☑ | Sufficiency FAIL aligns with epoch gap |
| 8 Novelty & fairness | ☑ | Multi-bug depth; anti-cheat strong; one fairness gap |
| 9 Long context | ☐ | N/A — not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Really solid task — the digest-pinned offline environment, live CLI/host workflow, pinned driver integrity checks, independent Python replay, and store/session artifact validation are all strong. Difficulty calibration looks right too. One fix before accept: in `http_contract.md`, the dual-epoch passcode materialization rule needs to spell out the blend behavior explicitly. Right now the doc says materialization should follow the passcode epoch, but the probe tests expect that when host and passcode epochs are within one step of each other, materialization resolves to the host epoch (otherwise passcode epoch). Several near-complete runs hit 40/41 and failed only on that edge case — a short worked example (e.g. host epoch one step ahead of passcode epoch) would close the gap.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | yes | 1 |
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
