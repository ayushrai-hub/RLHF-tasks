# Terminus Review Report: variform-ruby-transform-allowlist-audit

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed (report: 100% 3/3; solve.sh uses patches, no hardcode) |
| **CHECK count** | 40 |
| **UNCHECK count** | 15 |

**Error categories (internal):** Test Alignment/Coverage Issues

**Decision (concise):** Strong security-audit task with excellent behavioral coverage, anti-fixture generation, pinned environment, and correct flat (non-milestone) rubric format. One real blocker: several structural source-grep and keyword tests enforce reference-solution syntax/location/vocabulary beyond what `instruction.md` and `security-spec.md` state, and agent logs show functionally secure fixes (all exploits blocked, all valid specs pass) failing those meta-tests. Relax tests to behavior + owning-file outcomes, or document exact idioms in the spec.

**Insights (concise):**

- ChatGPT **Revise** call is **partially agree** — core blocker confirmed; Dockerfile/base-image and `#14` pip pinning are **not** blockers.
- Platform rubric is **correctly flat** for `number_of_milestones = 0` (no `# Rubric 2+` headers); **not** incorrectly in milestone format.
- `requirements.txt` pins with `==` + SHA-256 hashes; automated `#14` fail is a false positive.
- Worst-model 60% → observed **medium** tier; declared `hard` in `task.toml` is informational only (not a revision blocker).
- Behavioral exploit + generated-spec tests are robust; brittleness is isolated to white-box meta-checks (`test_scalar_scan_is_case_insensitive`, `test_method_gate_matches_exactly`, `test_security_notes_covers_all_themes`).
- Rubric positive sum ≈48 pts exceeds 10–40 guideline (Low only; not a blocker).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #29, #30, #55 | Structural meta-tests reject functionally correct secure fixes by enforcing reference-implementation syntax, file-local grep targets, and undocumented `security_notes.md` keyword sets — not just the behavioral contract in `instruction.md` / `security-spec.md`. | `tests/test_outputs.py:93-101` (`_method_gate_uses_exact_match` accepts only `ALLOWED.include?`/`==`, rejects e.g. `casecmp?`); `tests/test_outputs.py:109-114,318-323` (`_scalar_scan_is_case_insensitive` greps only `scalar_scan.rb` for `downcase`/`upcase`/`casecmp`, not behavior); `tests/test_outputs.py:490-548` (`test_security_notes_covers_all_themes` requires keyword sets like `"plus"`, `"sign"`, `"+write"` per theme group); `entire-report.txt:57-58,72-73,89-91,124-131` (agents 38–39/40 with all exploits blocked fail meta-tests); `docs/guidelines/common-errors.md:23` (grep-source anti-pattern) | Either (a) document required implementation idioms and `security_notes.md` vocabulary in `instruction.md` or `security-spec.md`, or (b) relax structural tests to validate outcomes (owning-file behavioral pass + note content tied to spec themes) instead of regex on specific files/idioms. |

*No other High/Medium blockers found.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Verifier over-constrains implementation details not in instruction/spec; `test_scalar_scan_is_case_insensitive`, `test_method_gate_matches_exactly`, `test_security_notes_covers_all_themes` reject equivalent secure fixes (ChatGPT High) | **Partially agree** | Behavioral tests pass for failed agents per `entire-report.txt:124-131`; structural helpers at `tests/test_outputs.py:93-101,109-114,535`. Instruction line 4 mitigates file-location for scalar scan but does not mandate `downcase` in `scalar_scan.rb` source vs callable helper elsewhere. |
| 2 | Behavioral coverage is strong; issue is brittle meta-checks not missing coverage (ChatGPT Medium) | **Agree** | 40 tests; exploit + generated hostile specs + valid corpus in `tests/test_outputs.py`; per-test stats `entire-report.txt:33-73`. |
| 3 | `keywords` field and high time estimates are minor polish (ChatGPT Low) | **Agree** | `task.toml:13-15`; non-standard `keywords` does not break execution. |
| 4 | Dockerfile FROM digest-pinned; Python base justified for Ruby task (ChatGPT) | **Agree** | `environment/Dockerfile:1-6` digest + justification comment; tmux/asciinema at lines 14-15. |
| 5 | `#14` pip unpinned (automated review) | **Disagree** | `environment/requirements.txt:1-9` all `package==version --hash=sha256:…`; Dockerfile line 21 uses `--require-hashes`. |
| 6 | Harbor review "READY TO USE" (entire-report) | **Partially agree** | Env/oracle structure sound; structural meta-test fairness gap remains. |
| 7 | LLMaJ `behavior_in_tests` pass (entire-report) | **Partially agree** | Behavioral reqs covered; white-box idiom reqs are unstated in instruction. |
| 8 | Instruction sufficiency FAIL — structural tests cause 0/4 debug pass despite functional security (entire-report) | **Agree** | `entire-report.txt:75-116,124-131`. |
| 9 | Non-milestone task uses milestone rubric format (user question) | **Disagree** | `task.toml:10` `number_of_milestones = 0`; platform rubric `entire-report.txt:376-399` is flat `Agent …, ±N` list with no `# Rubric N` headers — correct non-milestone format per `docs/guidelines/rubrics.md:64`. |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Two paragraph blocks (~398 words) | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineering audit tone; defers contract to security-spec | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables/code | `instruction.md` |
| 4 | CHECK | No step by step instructions | Describes outcome, not dev steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT not HOW; points to security-spec | `instruction.md` |
| 6 | CHECK | No design doc style tables | None | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear goal, paths, rejection contract, output file | `instruction.md`, `environment/docs/security-spec.md` |
| 8 | CHECK | Instruction is interesting | Realistic Ruby/ImageMagick injection audit | — |
| 9 | CHECK | Instruction is unique | CVE-inspired multi-file validation audit | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/environment/…` throughout | `instruction.md` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | None | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | apt + COPY only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `==` + hashes in requirements.txt; `--require-hashes` | `environment/requirements.txt`, `environment/Dockerfile:21` |
| 15 | CHECK | Base Docker image is pinned by digest | `@sha256:01f42367…` | `environment/Dockerfile:6` |
| 16 | CHECK | Environment does not use context from outside environment/ | COPY . from build context only | `environment/Dockerfile:25` |
| 17 | CHECK | Environment does not contain solution or ground truth | No patches/answers in env tree | `environment/` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | venv in Dockerfile; test.sh runs pytest only | `environment/Dockerfile:19-21`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Harbor oracle not run locally; report shows 100% | `entire-report.txt:26` |
| 22 | CHECK | Oracle does not require internet or downloading packages | patch + cp only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Applies patches to five validation files | `solution/solve.sh`, `solution/patches/` |
| 24 | CHECK | test.sh writes reward.txt; mkdir -p /logs/verifier | Canonical 0/1 block | `tests/test.sh:7-14` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No /oracle branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | 0 or 1 | `tests/test.sh:10-14` |
| 27 | UNCHECK | All tests aligned with instructions | Structural idiom/keyword reqs not in instruction/spec | `tests/test_outputs.py:93-101,109-114,490-548` |
| 28 | CHECK | Tests check for correctness, not just format | CLI exploit/valid corpus + clean rejection | `tests/test_outputs.py:223-465` |
| 29 | UNCHECK | Tests verify behavior, not implementation | Extensive source grep alongside behavior | `tests/test_outputs.py:85-140,246-436` |
| 30 | UNCHECK | No brittle exact string matching | Regex idiom gates + keyword theme lists | `tests/test_outputs.py:93-114,490-548` |
| 31 | CHECK | Tests have informative names or docstrings | All `test_*` docstrings present | `tests/test_outputs.py` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 5 negatives | `entire-report.txt:395-399` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All ±1,2,3,5 | `entire-report.txt:376-399` |
| 34 | CHECK | Each rubric line: Agent …, ±N | 24 Agent lines, flat format | `entire-report.txt:376-399` |
| 35 | CHECK | Rubric criteria detailed and precise | Task-specific trace checks | `entire-report.txt:376-399` |
| 36 | CHECK | Rubric uses positive language for negatives | Bad behavior phrased as failures | `entire-report.txt:395-399` |
| 37 | CHECK | Rubric does not reference /tests/ | No test refs | `entire-report.txt:376-399` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:376-399` |
| 39 | CHECK | Rubric does not mention oracle or NOP | None | `entire-report.txt:376-399` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | anonymous/ anonymous | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, category, timeouts, env | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | security/ruby match content | `task.toml:6-12` |
| 45 | UNCHECK | Difficulty matches observed agent pass rates | Declared `hard`; worst-model 60% → medium tier | `task.toml:8`, `entire-report.txt:16-22` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — regular task | `task.toml:10` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A | `task.toml:10` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A | `task.toml:10` |
| 50 | CHECK | Tests NOT baked into Docker image | COPY environment/ only | `environment/Dockerfile:25` |
| 51 | CHECK | Solution not accessible in environment | No solution/ in image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially pass by mutating inputs | Generated UUID specs + source checks | `tests/test_outputs.py:159-162,235-465` |
| 53 | CHECK | Git repos pinned to commit | No git clone | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% worst model) | Worst-model 60% | `entire-report.txt:20-22` |
| 55 | UNCHECK | Task is not too hard or unfair | Meta-tests reject secure equivalent implementations | `entire-report.txt:124-131`, blocker 1 |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 21, 27, 29, 30, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Valid specs plan cleanly | `test_valid_corpus_plans`, `test_boundary_valid_specs_still_plan` | covered | `tests/test_outputs.py:201-220` |
| Exploit specs refused via clean error path | `test_exploit_*`, `test_generated_*`, `assert_clean_rejection` | covered | `tests/test_outputs.py:165-181,223-465` |
| Drop pass-through methods from allow list | `test_allowlist_drops_passthrough_methods`, exploit tests | covered | `tests/test_outputs.py:85-90,246-251` |
| Method gate exact match (not substring) | `test_method_gate_matches_exactly`, smuggle tests | **phantom idiom** | Spec: `security-spec.md:45-48`; test also requires `ALLOWED.include?`/`==` only: `tests/test_outputs.py:93-101` |
| Case-insensitive option scan | `test_exploit_case_flag_rejected`, `test_scalar_scan_is_case_insensitive` | **phantom location/idiom** | Spec: `security-spec.md:63-66`; grep limited to `scalar_scan.rb` source: `tests/test_outputs.py:109-114,318-323` |
| Plus-form options equivalent to hyphen | `test_exploit_plus_flag_rejected` | covered (behavior) | `tests/test_outputs.py:326-341` |
| Hash keys scanned | `test_hash_scan_validates_keys`, hash exploit tests | covered | `tests/test_outputs.py:116-126,388-410` |
| Nested list/object recursion | `test_list_scan_recurses_into_nested_arguments`, nesting tests | covered | `tests/test_outputs.py:129-140,413-465` |
| Fixes in owning file, not CLI | `test_policy_stays_in_library` + structural file greps | partially covered | `instruction.md:4`; structural tests add idiom constraints beyond ownership |
| Write `security_notes.md` with subsystem, weakness, CWE, MIT | `test_security_notes_covers_all_themes` | **phantom keywords** | `instruction.md:5`; test adds 9 keyword theme groups: `tests/test_outputs.py:495-543` |
| No special-casing fixture names | generated UUID specs | covered | `tests/test_outputs.py:235-465` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27, blocker 1, spec alignment |
| `environment/docs/security-spec.md` | #7, spec alignment, adjudication |
| `environment/Dockerfile` | #13-20, #50 |
| `environment/requirements.txt` | #14 |
| `task.toml` | #42-45, milestone N/A, rubric format |
| `tests/test_outputs.py` | #27-31, #55, blocker 1, spec alignment |
| `tests/test.sh` | #20, #24 |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | #45, #54, agent stats, rubric #32-39, adjudication |
| `docs/guidelines/common-errors.md` | blocker 1 |
| `docs/guidelines/rubrics.md` | rubric format check |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: variform-ruby-transform-allowlist-audit/ ===
Summary: 0 error(s), 1 warning(s), 1 info
Task type detected: regular
WARNING: pinned_dependencies — false positive (requirements.txt uses == + hashes)
INFO: non-milestone task (milestone preferred, not blocked)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 meta-test failures |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 2 meta-test failures |
| oracle | 100.0% (3/3) | per report |
| nop | 0.0% (0/1) | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no (informational only) |

Per-test failures on meta-checks: `test_scalar_scan_is_case_insensitive` 8/10, `test_method_gate_matches_exactly` 9/10, `test_security_notes_covers_all_themes` 8/10 (`entire-report.txt:52-53,57-58,72-73`).

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder matches report; regular task, `number_of_milestones = 0` |
| 1 Instruction | ☑ | Concise audit prompt; security-spec authoritative |
| 2 Environment | ☑ | Digest-pinned Python base + Ruby apt; tmux/asciinema; no tests/solution in image |
| 3 Oracle | ☐ | Not run locally; solve.sh patches five files + security_notes |
| 4 Verifiers | ☑ | Behavioral strong; structural meta-tests unfair (blocker 1) |
| 5 Metadata | ☑ | `keywords` non-standard (Low); times high (Low) |
| 6 Rubric | ☑ | Flat non-milestone format correct; 5 negatives; ≈48 positive pts (Low) |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL confirmed; 60% pass rate calibrated |
| 8 Novelty & fairness | ☑ | Multi-file security reasoning; meta-test brittleness hurts fairness |
| 9 Long context | N/A | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid security audit task — the exploit fixtures, generated hostile specs, valid-corpus regression, and pinned environment are all in great shape, and the flat rubric format is correct for a non-milestone submission. The one thing blocking acceptance: a few verifier tests check for specific code patterns (`downcase` in `scalar_scan.rb`, `ALLOWED.include?` in the method gate, fixed keyword lists in `security_notes.md`) rather than just the behavior described in the spec. Agent logs show fixes that block every exploit and keep valid specs passing still failing those meta-checks. Please either spell out those exact implementation and documentation expectations in the prompt/spec, or relax those tests so equivalent secure fixes pass.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | no | — |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Metadata Issues | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Environment | no | — |
| Milestones | no | — |
