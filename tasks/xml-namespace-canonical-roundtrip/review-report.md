# Terminus Review Report: `xml-namespace-canonical-roundtrip`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 42 |
| **UNCHECK count** | 13 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong Go source-fix task with digest-pinned environment, normative contract, and thorough namespace tests. Two spec-test gaps drive revision: batch member directories are tested as extensionless filename stems (`drop` for `drop.xml`) but instruction/contract say only “basename”; duplicate-attribute rejection is tested for a specific error substring not documented in instruction or contract. Declared `hard` vs 60% worst-model pass rate is informational only (not a blocker). Platform rubric uses optional `# Rubric 1` header — acceptable for a non-milestone task.

**Insights (concise):**

- Agent failure analysis in `entire-report.txt` confirms batch directory naming is systematic (both failed trials used `drop.xml` dirs).
- Broken `MemberDir` in `environment/internal/report/batch.go:80-87` already strips extensions — agents mis-infer from ambiguous spec and regress working code.
- Duplicate error substring exists in `check/rules.go:22` but is not normative in instruction/contract; one trial failed on wording.
- Worst-model pass rate is 60% (GPT-5.5), within Medium tier — task is not too easy (#54 passes).
- `# Rubric 1` on a non-milestone task is allowed per `docs/guidelines/rubrics.md`; rubric has 3 distinct negatives and valid scoring.
- `test.sh` omits `mkdir -p /logs/verifier` (minor canonical-pattern gap; not a substantive fairness blocker).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Batch member directory naming is ambiguous in spec but tested as extensionless stem | `instruction.md:13` “named from each input basename”; `contract.md:10` `DIR/<basename>/`; `tests/test_outputs.py:101-106` expects `(batch_out / "drop").is_dir()` for input `drop.xml`; `batch.go:80-87` strips ext | Define member dir as `TrimSuffix(filepath.Base(input), filepath.Ext(input))` in `instruction.md` and `contract.md` with an example (`drop.xml` → `drop/`) |
| 2 | Medium | Test Alignment/Coverage Issues, Instruction Styling | #27, #30 | Duplicate-attribute test requires undocumented error substring | `instruction.md:17` requires rejection only; `tests/test_outputs.py:290` asserts `"duplicate attribute expanded name" in result.stdout`; not in `contract.md`; substring only in env source `check/rules.go:22` | Document required error text in contract (or instruction), or relax test to accept any clear duplicate-expanded-name error |

*Difficulty metadata mismatch (`task.toml:7` `hard` vs 60% worst-model Medium) is recorded in section 7 only — not a revision blocker per review policy.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | `task.toml` declares `hard` but report rates Medium; Claude 100%, GPT-5.5 60% — set metadata or harden (ChatGPT High) | Partially agree | `task.toml:7` `difficulty = "hard"`; `entire-report.txt:14-20` Medium, 100%/60%; worst model 60% = Medium tier per `docs/guidelines/difficulty.md`. Mismatch is real but **not a revision blocker** per `prompt.md` difficulty-calibration rules |
| 2 | Batch member directories: spec says “basename” but verifier expects stem without extension (ChatGPT High) | Agree | `instruction.md:13`, `contract.md:10` vs `tests/test_outputs.py:106,113`; `entire-report.txt:59-64` both trials used `drop.xml` dirs |
| 3 | Duplicate expanded-attribute error message tested more specifically than spec (ChatGPT High) | Partially agree | `tests/test_outputs.py:290` vs `instruction.md:17`; severity Medium — message exists in `check/rules.go:22` but not in normative docs; only one trial cited in failure analysis |
| 4 | LLMaJ `behavior_in_task_description` PASS | Disagree for batch naming | LLMaJ passed at line 119 but `instruction.md:13` “basename” contradicts `tests/test_outputs.py:106` stem expectation |
| 5 | LLMaJ `Task Instruction Sufficiency` FAIL on batch naming + error string | Agree | `entire-report.txt:43,79-83` systematic batch naming failure; aligns with artifact cross-check |
| 6 | Automated review: non-canonical Go base image (Warning) | Partially agree | `environment/Dockerfile:1` official golang image, digest-pinned; justified for Go toolchain — not a blocker |
| 7 | Test quality: unused `namespace_uris` filtering untested | Agree (non-blocker) | `contract.md:36` requires excluding unused URIs; no test fixture with unused declaration — coverage gap only |
| 8 | Test quality: `audit.jsonl` field coverage indirect | Agree (non-blocker) | `contract.md:43` specifies fields; Python tests delegate to validate/replay without direct field asserts |
| 9 | Non-milestone task uses milestone rubric format (`# Rubric 1`) | Disagree as blocker | `entire-report.txt:374` `# Rubric 1`; `docs/guidelines/rubrics.md:60` allows `# Rubric 1` optional on non-milestone; no `# Rubric 2+` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction is concise (1 sentence to 3 paragraphs max) | ~6 dense paragraph blocks plus code fence; spec-heavy | `instruction.md` |
| 2 | UNCHECK | Instruction reads like a natural prompt, not a spec document | Normative contract dump tone in L15–19 | `instruction.md:15-19` |
| 3 | CHECK | No excessive markdown formatting | Minimal markdown, one code block | `instruction.md` |
| 4 | CHECK | No step by step instructions | No solve walkthrough | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Describes outputs/behavior, not fix steps | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | Batch member dir naming ambiguous | `instruction.md:13`, `contract.md:10` |
| 8 | CHECK | Instruction is interesting | Real XML namespace canonicalization use case | — |
| 9 | CHECK | Instruction is unique | Distinct source-fix Go/XML task | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment`, `/app/output/...` | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task name string | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None found | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/` |
| 14 | CHECK | All Python/pip dependencies use pinned versions | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:18` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:1a6d4452...` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment directory | COPY limited to env tree | `environment/Dockerfile:29-35` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | Intentional bugs only; no walkthrough | `environment/internal/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:18`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Not executed locally this session | — |
| 22 | CHECK | Oracle does not require internet or downloading packages | `GOPROXY=off`; local go build | `environment/Dockerfile:25`, `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Writes real Go fixes, builds, tests | `solution/solve.sh` |
| 24 | UNCHECK | test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path | Missing `mkdir -p /logs/verifier` | `tests/test.sh:8-14` |
| 25 | CHECK | Verifiers use exact same logic for oracle and agent runs | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | Writes 0 or 1 | `tests/test.sh:10-14` |
| 27 | UNCHECK | All tests aligned with instructions | Batch dir naming + error substring gaps | §2 blockers |
| 28 | CHECK | Tests check for correctness, not just format | Byte-level canonical XML + replay/validate | `tests/test_outputs.py` |
| 29 | CHECK | Tests verify behavior, not implementation | CLI output assertions, no source grep | `tests/test_outputs.py` |
| 30 | UNCHECK | No brittle exact string matching where flexible checks would work | Duplicate error substring is brittle vs spec | `tests/test_outputs.py:290` |
| 31 | CHECK | Tests have informative names or docstrings | All 10 `test_*` functions have docstrings | `tests/test_outputs.py:60-282` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 3 negatives (-5, -3, -3) | `entire-report.txt:386-388` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All criteria use allowed scores | `entire-report.txt:375-388` |
| 34 | CHECK | Each rubric criterion one line starting with Agent, comma, score | Format matches | `entire-report.txt:375-388` |
| 35 | CHECK | Rubric criteria are detailed and precise | Task-specific file/behavior criteria | `entire-report.txt:375-388` |
| 36 | CHECK | Rubric criteria use positive language | Bad behavior scored negative | `entire-report.txt:386-388` |
| 37 | CHECK | Rubric does not reference testing logic or /tests/ | No /tests/ references | `entire-report.txt:375-388` |
| 38 | CHECK | Rubric does not reference metadata or instruction.md | No task.toml/instruction refs | `entire-report.txt:375-388` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | None | `entire-report.txt:375-388` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Both set | `task.toml:5-6` |
| 43 | CHECK | All other required metadata fields present | category, tags, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | go/xml/data-processing match content | `task.toml:7-13` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst model 60% = Medium | `task.toml:7`, `entire-report.txt:19-20` |
| 46 | UNCHECK | steps/ layout present | N/A — `number_of_milestones = 0` | `task.toml:12` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:12` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:12` |
| 49 | UNCHECK | Each milestone test scoped to milestone | N/A | `task.toml:12` |
| 50 | CHECK | Tests NOT baked into Docker image | `.dockerignore` excludes tests/ | `environment/.dockerignore:17` |
| 51 | CHECK | Solution not accessible in environment | solution/ excluded | `environment/.dockerignore:16` |
| 52 | CHECK | Agent cannot modify input data to trivially pass | Dynamic XML in tests; broken source must be fixed | `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst model 60% | `entire-report.txt:19-20` |
| 55 | UNCHECK | Task is not too hard or unfair | Undocumented batch dir rule caused systematic agent failures | `entire-report.txt:59-64`, §2 blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 25, 26, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 2, 7, 21, 24, 27, 30, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / contract) | Test(s) | Status | Proof |
|--------------------------------------|---------|--------|-------|
| Batch member dirs named from input basename | `test_batch_rerun_evicts_stale_member_directories` | gap | `instruction.md:13`, `contract.md:10` vs `test_outputs.py:106` expects `drop` not `drop.xml` |
| Reject duplicate expanded-name attributes | `test_ambiguous_attributes_are_rejected` | gap | `instruction.md:17` vs `test_outputs.py:290` exact substring |
| Equivalent inputs → identical `canonical_sha256` | `test_batch_equivalent_inputs_identical_canonical_digest` | covered | `test_outputs.py:60-95` |
| Batch re-run evicts stale member directories | `test_batch_rerun_evicts_stale_member_directories` | covered | `test_outputs.py:98-116` (dir naming aside) |
| Lexicographic n-prefix for attribute-only namespaces | `test_attribute_only_namespace_prefix_order` | covered | `test_outputs.py:119-135` |
| Prefix rebinding sibling isolation | `test_prefix_rebinding_sibling_isolation_and_replay` | covered | `test_outputs.py:138-155` |
| Element-local `declared` bindings in scope.json | `test_scope_declared_bindings_are_element_local` | covered | `test_outputs.py:158-170` |
| Default namespace reset / sibling isolation | `test_deep_default_reset_sibling_isolation`, `test_default_namespace_reset_scope_artifacts_and_cleanup` | covered | `test_outputs.py:172-233` |
| Unprefixed attributes remain local under default NS | `test_unprefixed_attributes_remain_local_under_default_namespace` | covered | `test_outputs.py:236-256` |
| Output directory reuse replaces prior artifacts | `test_multi_run_output_directory_replaces_prior_artifacts` | covered | `test_outputs.py:259-278` |
| `namespace_uris` excludes unused declarations | — | gap (non-blocker) | `contract.md:36`; no unused-declaration fixture |
| `audit.jsonl` rows include input, output, unix_ms | — | gap (non-blocker) | `contract.md:43`; indirect via validate only |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #2, #7, #10, #27, blocker 1–2, spec alignment |
| `task.toml` | #45, #46–49, metadata |
| `environment/docs/contract.md` | blocker 1–2, spec alignment |
| `environment/internal/report/batch.go` | blocker 1 (MemberDir strips ext) |
| `environment/internal/check/rules.go` | blocker 2 (error string in source) |
| `environment/Dockerfile` | #14–20, #50 |
| `environment/.dockerignore` | #50, #51 |
| `tests/test.sh` | #24, #26 |
| `tests/test_outputs.py` | #27–31, blockers, spec alignment |
| `solution/solve.sh` | #22–23 |
| `entire-report.txt` | agent stats, external adjudication, rubric |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: xml-namespace-canonical-roundtrip/ ===
Summary: 0 error(s), 1 warning(s), 1 info
WARNING: informative_test_docstrings — module-level docstring missing
INFO: submission-diversity — non-milestone task (not blocked)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| terminus-claude-opus-4-8 | 100.0% (5/5) | Best model |
| oracle | 100.0% (3/3) | From platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | Medium |
| Declared difficulty | hard |
| Tier match (#45) | no — informational only, not a revision blocker |

Per-test pass rates (`entire-report.txt:31-40`): lowest are `test_batch_rerun_evicts_stale_member_directories` (8/10) and several at 9/10 — consistent with spec-gap failures, not random env flakes.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task matches report; regular layout; Go source-fix |
| 1 Instruction | ☑ | Dense spec; batch naming ambiguous |
| 2 Environment | ☑ | Digest-pinned Go image; tmux/asciinema; GOPROXY=off |
| 3 Oracle | ☐ | Not executed locally (Docker/Harbor unavailable in session) |
| 4 Verifiers | ☑ | 10 behavior tests; reward block present; mkdir missing |
| 5 Metadata | ☑ | Complete; non-milestone |
| 6 Rubric | ☑ | Platform rubric in report — valid non-milestone format |
| 7 LLMaJ & agent evidence | ☑ | Cross-checked; batch naming failure systematic |
| 8 Novelty & fairness | ☑ | Multi-file bugs; spec gap unfair on batch naming |
| 9 Long context | ☐ | N/A — not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Really solid work on this one — the Go environment is well set up, the contract doc is thorough, and the namespace test scenarios (prefix rebinding, default reset, batch equivalence) are genuinely challenging. Two spec gaps to fix before accept: batch member directories need to be documented as the filename stem without extension (e.g. `drop.xml` → `drop/`, not `drop.xml/`) in both `instruction.md` and `contract.md` — agents are consistently getting this wrong from the current “basename” wording. Also either document the duplicate-attribute error substring (`duplicate attribute expanded name`) in the contract or loosen that one assertion so agents aren’t penalized for a reasonable error message. Optional polish: add `mkdir -p /logs/verifier` to `test.sh`. Consider setting difficulty to `medium` to match observed rates, though that alone wouldn’t block accept once the spec fixes land.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1, 2 |
| Test Alignment/Coverage Issues | yes | 1, 2 |
| Task Difficulty | no | — (60% worst model; metadata mismatch informational) |
| Metadata Issues | no | — |
| Milestones | no | — |
| Rubric | no | — (`# Rubric 1` acceptable for non-milestone) |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — (mkdir is minor) |
