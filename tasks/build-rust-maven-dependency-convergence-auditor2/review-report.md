# Terminus Review Report: `build-rust-maven-dependency-convergence-auditor2`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass |
| **CHECK count** | 49 |
| **UNCHECK count** | 6 |

**Error categories (internal):** none

**Decision (concise):** No material blockers on re-audit. Digest-pinned canonical Rust base, offline verifier, independent Python policy oracle, fixture immutability, and anti-cheat design are solid. Declared `hard` matches worst-model Claude Opus 4.8 at 0% (GPT-5.5 at 100% still qualifies as Hard per `docs/guidelines/difficulty.md`). Automated `terminus review` blockers on #14 (pip), #45/#54 (difficulty), and the external report’s non-canonical-base warning are false positives. Platform rubric (lines 305–315 of `entire-report.txt`) is correctly formatted as a **non-milestone** flat rubric, not milestone `# Rubric N` blocks. Instruction length (#1/#2) exceeds style guidelines but is normatively required for this output surface — not a functional blocker.

**Insights (concise):**

- Oracle passes (`./scripts/terminus oracle` → reward 1.0); `solve.sh` copies ~900-line `main.rs` and runs `cargo --offline`.
- Verifier uses independent `load_model()` in `tests/test_outputs.py` — no golden-file shortcut; `EXPECTED_FIXTURE_TREE_SHA256` blocks fixture tampering.
- `original_coord` fallback in test oracle (`test_outputs.py:250`) and solution (`solution/src/main.rs:282`) is **not stated** in `instruction.md:6`, but **no fixture** exercises a version-resolution path that depends on it (verified by fixture scan).
- Rust `1.85-slim` with digest `sha256:9f841bbe…` is listed in `docs/guidelines/dockerfxile.md` — canonical, not an exception.
- Apt micro-version pins (`Dockerfile:9-13`) are brittle maintenance risk (Medium), not a High acceptance blocker.
- Agent failures are implementation traps (JSON key order, Maven logic) — not spec gaps; 2/10 timeouts below blocking threshold.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| — | — | — | — | — | — | — |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | ChatGPT: Accept, no High/Medium/Low issues | **Agree** | Full artifact re-audit; no High gaps found |
| 2 | ChatGPT: digest-pinned Rust, offline verifier, policy oracle, anti-cheat solid | **Agree** | `environment/Dockerfile:1,21-27`; `tests/test_outputs.py:22,505-509`; `environment/.dockerignore:17-18` |
| 3 | ChatGPT: hard difficulty supported; 2/10 timeouts not blocking | **Agree** | `entire-report.txt:22-38`; `task.toml:6` |
| 4 | ChatGPT: apt pins / canonical-base are maintenance, not blockers | **Agree** | Apt pins = Medium per `reviewer-checklist-full.md:46`; Rust base is canonical in `docs/guidelines/dockerfxile.md:14-15` |
| 5 | entire-report: Difficulty HARD, Claude 0%, GPT 100% | **Agree** | `entire-report.txt:22-28`; worst-model 0% → Hard tier |
| 6 | entire-report: Quality checks all PASS (behavior_in_task_description, anti_cheat, etc.) | **Agree** | Cross-checked `instruction.md` ↔ `tests/test_outputs.py`; 8 tests with docstrings |
| 7 | entire-report: RECOMMENDATION NEEDS REVISION (apt pins, non-canonical base) | **Disagree** | Rust image is canonical (`dockerfxile.md:14-15`); apt pins are Medium maintenance only |
| 8 | entire-report: Test-quality — BOM/original_coord fallback unstated in instruction | **Partially agree** (Low) | `test_outputs.py:250` tries `original_coord` in DM/BOM lookup; no fixture depends on it; agents following instruction literal rules still grade correctly on current fixtures |
| 9 | entire-report: expert 600 min vs 1200s agent timeout over-scoped | **Partially agree** (Low) | `task.toml:13-14,19`; metadata plausibility note only — not a blocker |
| 10 | Automated `terminus review`: #14 pip unpinned | **Disagree** | `environment/Dockerfile:22-27` — all six packages use `==` pins |
| 11 | Automated `terminus review`: #45/#54 difficulty mismatch (worst 100%) | **Disagree** | Worst model is Claude **0%** (`entire-report.txt:27`), not GPT 100%; Hard tier valid |
| 12 | Automated `terminus review`: #1 instruction too long (875 words) | **Partially agree** (style) | `instruction.md` = 875 words; normative contract required for tested surface; UNCHECK #1/#2 but not Revise driver |
| 13 | Agent analysis: JSON key order is implementation trap, not spec gap | **Agree** | `instruction.md:12` specifies key order; failures are serde ordering bugs |
| 14 | Agent analysis: no cheating, no reward hacking | **Agree** | `entire-report.txt:76-77`; stub `environment/app/src/main.rs` outputs empty/wrong data |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | 875 words / 19 normative bullets exceeds length guideline | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Dense normative contract; opening paragraph + rule bullets | `instruction.md:1-20` |
| 3 | CHECK | No excessive markdown formatting | Plain bullets, no ##/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step by step instructions | No dev workflow steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | States Maven rules (WHAT), not Rust implementation (HOW) | `instruction.md` |
| 6 | CHECK | No design doc style tables | No input→output mapping tables | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear CLI contract, schemas, edge rules | `instruction.md:1-20` |
| 8 | CHECK | Instruction is interesting | Real Maven convergence / SBOM audit use case | `instruction.md` |
| 9 | CHECK | Instruction is unique | Rust CLI + Maven semantics + dual JSON/CSV output uncommon in corpus | task domain |
| 10 | CHECK | All paths absolute | `/app/...` throughout | `instruction.md:1` |
| 11 | CHECK | Task name not in instruction | No task slug in text | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md` |
| 13 | CHECK | Dockerfile no web content fetch | `cargo fetch` at build only | `environment/Dockerfile:31` |
| 14 | CHECK | Python/pip pinned with == | Six packages pinned | `environment/Dockerfile:22-27` |
| 15 | CHECK | Base image digest-pinned | `@sha256:9f841bbe…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context stays in environment/ | COPY app/ only | `environment/Dockerfile:29-33` |
| 17 | CHECK | No ground truth in environment | Stub `main.rs`; README is schema docs only | `environment/app/src/main.rs`, `environment/app/README.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image; test.sh no runtime installs | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:21-27`, `tests/test.sh:16-17` |
| 21 | CHECK | Oracle passes consistently | `./scripts/terminus oracle` → reward 1.0 | oracle run 2026-06-26 |
| 22 | CHECK | Oracle no internet | `cargo build/run --offline` | `solution/solve.sh:26-27` |
| 23 | CHECK | Oracle derives answer | Full Rust implementation, not echo | `solution/src/main.rs` |
| 24 | CHECK | test.sh reward.txt + failure path | Canonical block | `tests/test.sh:6-24` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `tests/test.sh` |
| 26 | CHECK | Binary rewards only | 0 or 1 | `tests/test.sh:20-23` |
| 27 | CHECK | Tests aligned with instructions | All instruction rules traced to tests; `original_coord` fallback unused by fixtures | `tests/test_outputs.py`, fixture scan |
| 28 | CHECK | Tests check correctness | Independent policy model equality | `tests/test_outputs.py:505-509` |
| 29 | CHECK | Behavior not implementation grep | No source grepping | `tests/test_outputs.py` |
| 30 | CHECK | Not brittle where flexible OK | Exact byte match required by instruction contract | `instruction.md:17-20` |
| 31 | CHECK | Informative test docstrings | All 8 `test_*` have docstrings | `tests/test_outputs.py:484-577` |
| 32 | CHECK | Rubric ≥3 negatives | 4 negatives in platform rubric | `entire-report.txt:312-315` |
| 33 | CHECK | Rubric scores ∈ {±1,2,3,5} | +5/-5/-3 only | `entire-report.txt:305-315` |
| 34 | CHECK | Rubric `Agent …, ±N` format | All lines match | `entire-report.txt:305-315` |
| 35 | CHECK | Rubric criteria detailed | Task-specific Maven/Rust trace checks | `entire-report.txt:305-311` |
| 36 | CHECK | Rubric positive language | Bad behaviors with negative scores | `entire-report.txt:312-315` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:305-315` |
| 38 | CHECK | Rubric no instruction.md/task.toml refs | None | `entire-report.txt:305-315` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:305-315` |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README at task root | task root |
| 42 | CHECK | author_name/email present | anonymous / anonymous | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields present | category, timeouts, environment block | `task.toml` |
| 44 | CHECK | Tags/languages/category match | rust, maven, build-and-dependency-management | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches pass rates | `hard` + worst-model 0% (Claude) | `task.toml:6`, `entire-report.txt:27` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:9` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:9` |
| 49 | UNCHECK | Milestone test scope | N/A | `task.toml:9` |
| 50 | CHECK | Tests not baked in image | `.dockerignore` excludes tests/ | `environment/.dockerignore:18` |
| 51 | CHECK | Solution not in environment | solution/ excluded | `environment/.dockerignore:17` |
| 52 | CHECK | Agent can't trivially mutate inputs | SHA256 fixture tree check | `tests/test_outputs.py:22,525-528` |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 0% << 80% threshold | `entire-report.txt:27` |
| 55 | CHECK | Not too hard/unfair | Spec complete; failures are implementation bugs | `entire-report.txt:50-82` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 1, 2, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction) | Test(s) | Status | Proof |
|---------------------------|---------|--------|-------|
| CLI command + output paths | `test_outputs_exist_and_only_documented_outputs` | covered | `instruction.md:1`, `test_outputs.py:484-489` |
| JSON top-level key order | `test_json_schema_key_order_and_totals` | covered | `instruction.md:12`, `test_outputs.py:497` |
| Full JSON correctness | `test_json_report_matches_policy_model` | covered | `instruction.md:3-16`, `test_outputs.py:505-509` |
| CSV schema, sorting, LF, no trailing newline | `test_audit_csv_sorting_line_endings_and_contents` | covered | `instruction.md:17-19`, `test_outputs.py:512-522` |
| Fixture immutability + pretty JSON | `test_fixture_immutability_and_pretty_json` | covered | `instruction.md:20`, `test_outputs.py:525-532` |
| DM, type/classifier, qualifiers, relocations | `test_dependency_management_type_classifier_and_qualifiers` | covered | `instruction.md:3-10`, `test_outputs.py:535-552` |
| Ignored/optional, ranges, CVE suppression | `test_ignored_optional_ranges_and_cve_suppression` | covered | `instruction.md:8-10`, `test_outputs.py:555-574` |
| Module/license summaries + audit edge rows | `test_summaries_and_audit_edge_rows_are_present` | covered | `instruction.md:14-19`, `test_outputs.py:577-606` |
| DM/BOM lookup on pre-relocation coordinate | — | gap (inactive) | `test_outputs.py:250`; no fixture triggers path |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #2, #5, #7, #10, spec alignment |
| `task.toml` | #42-45, milestone N/A |
| `environment/Dockerfile` | #13-20, #14, #15, canonical base |
| `environment/.dockerignore` | #50, #51 |
| `environment/app/src/main.rs` | #17 stub |
| `environment/app/README.md` | #17 schema docs |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment, anti-cheat |
| `solution/solve.sh` | #21-23 |
| `solution/src/main.rs` | #23 |
| `entire-report.txt` | #45, #54, rubric #32-39, agent stats |
| `docs/guidelines/dockerfxile.md` | canonical base adjudication |
| `docs/guidelines/difficulty.md` | #45, #54 tier rules |
| `docs/guidelines/rubrics.md` | rubric format (non-milestone) |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate build-rust-maven-dependency-convergence-auditor2/
Summary: 0 error(s), 1 warning(s), 2 info
- WARN: pinned_dependencies false positive on pip (packages are == pinned)
- INFO: non-milestone preferred; trailing exit in test.sh harmless
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 100% (5/5) | Full passes |
| terminus-claude-opus-4-8 | 0% (0/5) | 2 timeouts, 3 logic/compile failures |
| oracle | 100% (3/3 report; 1/1 local) | Consistent |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Regular (non-milestone) Rust build task; report matches folder |
| 1 Instruction | ☑ | Long but complete; #1/#2 style UNCHECK only |
| 2 Environment | ☑ | Canonical Rust digest; tmux+asciinema; pip pinned |
| 3 Oracle | ☑ | Passes locally; derives via full implementation |
| 4 Verifiers | ☑ | Independent model; 8 tests; reward block canonical |
| 5 Metadata | ☑ | `allow_internet=false`; hard tier valid |
| 6 Rubric | ☑ | Flat non-milestone format correct; 35 pos / 4 neg; not milestone blocks |
| 7 Agent evidence | ☑ | Claude 0% supports hard; timeouts 2/10 OK |
| 8 Novelty & fairness | ☑ | No cheating paths; stub prevents baked answers |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Accepted. The digest-pinned canonical Rust environment, offline verifier setup, exhaustive but testable instruction contract, independent Python policy oracle, fixture immutability checks, and anti-cheat design are solid. Oracle passes consistently; worst-model Claude at 0% supports declared hard difficulty (GPT-5.5 at 100% does not alone make the task too easy). Platform rubric uses correct flat non-milestone format with 4 negatives. Instruction length exceeds style guidelines but is required for the normative output contract — not a functional blocker. Apt micro-version pins are optional maintenance polish.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | no (style UNCHECK only) | — |
| Test Alignment/Coverage Issues | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Rubric | no | — |

*No applicable blocker categories.*
