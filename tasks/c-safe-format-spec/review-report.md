# Terminus Review Report: c-safe-format-spec

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (platform export 100% 3/3; local run blocked — no Docker) |
| **CHECK count** | 51 |
| **UNCHECK count** | 4 |

**Error categories (internal):** none

**Decision (concise):** Strong C format-string / spec-implementation task with a precise sfmt contract, 654+ held-out byte-exact corpus vectors, dynamic nonce anti-hardcoding, and source-integrity guards. Oracle passes, nop fails, worst-model 60% (medium tier). Platform rubric is correctly **flat** (non-milestone), 34 positive points, 4 distinct negatives. Automated audit FAILs on #14/#20 are false positives — deps are hash-pinned in `requirements.txt` and baked into the image. No blocking spec, test, environment, or rubric issues found.

**Insights (concise):**

- ChatGPT Accept verdict confirmed after artifact re-audit; no High/Medium blockers.
- `#14` / `#20` audit FAILs are regex false positives (`==`/`pytest` not on the `pip install` line; pytest installed via locked `requirements.txt`).
- Non-milestone rubric uses correct **flat** `Agent …, ±N` layout — no `# Rubric 2+` milestone headers.
- `security_notes.md` test is keyword-shallow (misses `va_list`/type-checked mention) — Low only; core formatter is exhaustively tested.
- Declared `hard` vs platform `medium` is informational per difficulty policy; worst-model 60% is acceptable calibration.
- Agent failures (~93% per-trial test pass in sufficiency analysis) trace to grouped-zero-pad implementation gaps, not spec omissions — spec has worked examples at `sfmt-spec.md:166,247`.

---

## 2. Main blockers

No blockers — task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | No High-severity spec/test/environment/rubric blockers (ChatGPT) | **Agree** | Full artifact pass; see sections 4–5 |
| 2 | Spec explicit on grouped zero-padding, 0o/0b prefixes, UTF-8 precision, %n rejection, typed args (ChatGPT) | **Agree** | `instruction.md:3-5`; `sfmt-spec.md:166,190,218`; dynamic tests `test_grouped_zero_pad`, `test_percent_n_rejected`, `test_utf8_precision_counts_codepoints` |
| 3 | Oracle passes, nop fails; agent misses are implementation gaps (ChatGPT) | **Agree** | `entire-report.txt:28-30` oracle 100% 3/3, nop 0%; sufficiency analysis `entire-report.txt:749-750` "None" systematic instruction issues |
| 4 | Non-milestone rubric flat, 34 positive pts, distinct negatives (ChatGPT) | **Agree** | `entire-report.txt:978-993` — flat `Agent …, ±N` list, no `# Rubric N` headers; `./scripts/terminus rubric-points` → 34/40; 4 negatives at lines 989-992 |
| 5 | Optional: task.toml `hard` vs platform MEDIUM (ChatGPT Low) | **Agree (Low, non-blocking)** | `task.toml:8` `hard`; `entire-report.txt:20` `Difficulty: ✅ MEDIUM`; policy: metadata mismatch never blocks |
| 6 | Optional: security_notes test keyword-only (ChatGPT / test quality review) | **Agree (Low, non-blocking)** | `tests/test_outputs.py:280-287` checks format-string/cwe-134/%n only; `instruction.md:5` also requires type-checked no-va_list mention |
| 7 | Optional: WORKDIR `/app/environment` non-canonical (Harbor review) | **Agree (Low, non-blocking)** | `environment/Dockerfile:20`; `task.toml:24` `workdir = "/app/environment"` — internally consistent |
| 8 | Dockerfile digest-pinned Python base acceptable (ChatGPT) | **Agree** | `environment/Dockerfile:1` `@sha256:01f42367…`; gcc/make/tmux/asciinema installed |
| 9 | `#14` unpinned pip (automated audit) | **Disagree** | `requirements.txt:1-9` uses `package==version --hash=sha256:…`; `Dockerfile:17-18` `--require-hashes -r /tmp/requirements.txt` |
| 10 | `#20` pytest not in Dockerfile (automated audit) | **Disagree** | pytest==8.4.1 in `requirements.txt:6`; venv at `/opt/verifier-venv`; `tests/test.sh:11` uses venv python, no runtime install |
| 11 | `#36` rubric negative phrasing (automated review script) | **Disagree** | Audit PASS: no `Agent does not…, +N` lines; negatives correctly use `-N` scores (`entire-report.txt:989-992`) |
| 12 | LLMaJ `behavior_in_task_description` PASS | **Agree** | `entire-report.txt:772`; cross-checked instruction + normative `sfmt-spec.md` |
| 13 | LLMaJ `behavior_in_tests` PASS | **Agree with caveat** | `entire-report.txt:773`; caveat: `security_notes` va_list/type-checked aspect partially untested (Low) |
| 14 | Harbor review "READY TO USE" | **Agree** | Warnings cosmetic only; no contract contradictions |
| 15 | Non-milestone task uses milestone rubric format (user query) | **Disagree** | `task.toml:10` `number_of_milestones = 0`; platform rubric has no `# Rubric 2+` blocks — flat list per `docs/guidelines/rubrics.md:66` |
| 16 | `#44` category security mismatch (automated audit heuristic) | **Disagree** | CWE-134 format-string task with `%n` refusal and security_notes; `category = "security"` fits `docs/task-type-taxonomy.md:16` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 3 prose paragraphs, ~229 words | `instruction.md` |
| 2 | CHECK | Natural prompt tone | Problem narrative, not synthetic walkthrough | `instruction.md` |
| 3 | CHECK | No excessive markdown | No headers/tables/code blocks | `instruction.md` |
| 4 | CHECK | No step-by-step HOW | States outcome + spec ref, not module steps | `instruction.md` |
| 5 | CHECK | WHAT not HOW hints | Defers contract to `sfmt-spec.md` | `instruction.md:3` |
| 6 | CHECK | No design-doc tables in instruction | No I/O mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Absolute paths, build command, output artifact | `instruction.md` |
| 8 | CHECK | Interesting | Deep C systems / format-string security task | task content |
| 9 | CHECK | Unique | Specialized sfmt contract + 654-vector corpus; no duplicate in review scope | subjective |
| 10 | CHECK | Absolute paths | All paths absolute (`/app/environment/...`) | `instruction.md` |
| 11 | CHECK | No task name in instruction | Folder name absent | `instruction.md` |
| 12 | CHECK | No canary strings | None detected | `instruction.md` |
| 13 | CHECK | No runtime web fetch in env | Offline; `allow_internet = false` | `task.toml:30`, `environment/` |
| 14 | CHECK | Pinned pip deps | `==` + `--hash=sha256:` in requirements; `--require-hashes` install | `requirements.txt`, `Dockerfile:17-18` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:` on Python base | `Dockerfile:1` |
| 16 | CHECK | Build context scoped | COPY only under environment | `Dockerfile:22` |
| 17 | CHECK | No ground truth in env | Stub returns NOT_IMPLEMENTED; spec is normative contract not oracle | `environment/src/format.c:11`, `sfmt-spec.md` |
| 18 | CHECK | No dangerous Docker ops | No privileged/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose mounts unchanged | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest stack in venv via Dockerfile; test.sh no installs | `Dockerfile:17-18`, `tests/test.sh:11` |
| 21 | CHECK | Oracle passes | Platform export: oracle 100% (3/3); local blocked (no Docker) | `entire-report.txt:28-30` |
| 22 | CHECK | Oracle offline | solve.sh copies C impl + make only | `solution/solve.sh:4-10` |
| 23 | CHECK | Oracle derives output | 457-line `format.c` implementation, not hardcoded bytes | `solution/solve.sh:6`, LLMaJ `hardcoded_solution` pass |
| 24 | CHECK | Canonical reward block | Writes 0/1 to reward.txt on pass/fail | `tests/test.sh:9-16` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `tests/test.sh` |
| 27 | CHECK | Tests aligned with instructions | All instruction behaviors traced to tests; minor Low gap on security_notes va_list keyword only | `instruction.md`, `tests/test_outputs.py`; phantom `>=250` corpus guard is anti-trim sanity check |
| 28 | CHECK | Tests check correctness | 654+ byte-exact corpus + dynamic behavioral tests | `tests/test_outputs.py:119-256` |
| 29 | CHECK | Behavior not implementation grep | Primary grading is CLI byte-exact output; source reads are anti-cheat guards only | `test_corpus_byte_exact`, `test_core_is_implemented:262-268` |
| 30 | CHECK | Not brittle string matching | Byte-exact required by spec contract | `instruction.md:3`, `sfmt-spec.md` |
| 31 | CHECK | Informative test names/docstrings | All 22 `test_*` have docstrings | `tests/test_outputs.py` |
| 32 | CHECK | ≥3 negative rubric criteria | 4 negatives | `entire-report.txt:989-992` |
| 33 | CHECK | Rubric scores in ±1,2,3,5 | All lines use allowed magnitudes | `entire-report.txt:978-993` |
| 34 | CHECK | Agent …, ±N format | 15 properly formatted lines | `entire-report.txt:978-993` |
| 35 | CHECK | Rubric detailed; positive cap | 34 positive pts (≤40); flat non-milestone list | `terminus rubric-points` |
| 36 | CHECK | Positive rubric language | No `Agent does not…, +N` lines | audit `rubrics.py:86-89` |
| 37 | CHECK | Rubric avoids /tests/ | No pytest or /tests/ references | platform rubric |
| 38 | CHECK | Rubric avoids instruction.md/task.toml | References spec paths and behavior only | platform rubric |
| 39 | CHECK | Rubric avoids oracle/NOP | No oracle/NOP mentions | platform rubric |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README in task folder | task tree |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | CHECK | Other metadata fields | category, tags, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | security + c + format-string + cwe-134 match content | `task.toml:6-13` |
| 45 | CHECK | Difficulty field present | `hard` in task.toml; worst-model 60% → medium tier (informational) | `task.toml:8`, `entire-report.txt:25-26` |
| 46 | UNCHECK | Milestone steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:10` |
| 47 | UNCHECK | Per-milestone solveN.sh | N/A | `task.toml:10` |
| 48 | UNCHECK | Per-milestone test_mN.py | N/A | `task.toml:10` |
| 49 | UNCHECK | Milestone test scoping | N/A | `task.toml:10` |
| 50 | CHECK | Tests not in image | No COPY tests/; `.dockerignore` excludes tests | `Dockerfile:22`, `environment/.dockerignore:13` |
| 51 | CHECK | Solution not in env | No solution/ COPY; stub only in env | `environment/.dockerignore:12`, `format.c:11` |
| 52 | CHECK | Agent cannot trivially cheat | Held-out corpus + UUID nonces + stdlib-divergence test | `tests/test_outputs.py:185-205`, corpus outside image |
| 53 | CHECK | Git clones pinned | No git clone in Dockerfile | `Dockerfile` |
| 54 | CHECK | Not too easy | Worst-model 60% ≤80% | `entire-report.txt:25-26` |
| 55 | CHECK | Not unfair | Spec covers grouped-zero-pad edge cases; agent failures are implementation | `sfmt-spec.md:166,247`; `entire-report.txt:749-750` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Implement `sf_format` per `sfmt-spec.md` byte-exact | `test_corpus_byte_exact`, `test_shipped_examples` | covered | `instruction.md:3`, 654+ vectors |
| Refuse `%n` (CWE-134) | `test_percent_n_rejected` | covered | `tests/test_outputs.py:193-196` |
| Binary + underscore-grouped decimal | corpus + `test_stdlib_shortcut_diverges` | covered | `tests/test_outputs.py:199-205` |
| 0o/0b alternate prefixes | corpus + `test_stdlib_shortcut_diverges` | covered | `tests/test_outputs.py:202-203` |
| Grouped zero-padding | `test_grouped_zero_pad`, `test_grouped_zero_pad_boundary` | covered | `tests/test_outputs.py:214-249` |
| Dynamic width/precision `*` / `.*` | `test_dynamic_width_precision` | covered | `tests/test_outputs.py:222-230` |
| UTF-8 code-point precision | `test_utf8_precision_counts_codepoints` | covered | `tests/test_outputs.py:208-211` |
| Alt-form prefix suppressed on zero | `test_alt_form_prefix_suppressed_on_zero` | covered | `tests/test_outputs.py:233-238` |
| Grouping on unsigned `%u` | `test_grouping_applies_to_unsigned` | covered | `tests/test_outputs.py:252-256` |
| Build with `make`; CLI `sfmt fmt <file>` | `test_binary_builds`, `run_vec` | covered | `tests/test_outputs.py:55-73` |
| `security_notes.md` naming CWE-134, %n, type-checked design | `test_security_notes_written` | partial (Low) | `instruction.md:5` vs `tests/test_outputs.py:285-287` — va_list/type-checked not asserted |
| Do not forward to printf/snprintf | `test_stdlib_shortcut_diverges` + corpus | covered | `instruction.md:3`, `tests/test_outputs.py:199-205` |
| Anti-hardcoding / stub replaced | `test_generated_nonce_roundtrips`, `test_core_is_implemented` | covered | `tests/test_outputs.py:185-190,262-268` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-7, #10-12, spec alignment |
| `task.toml` | #43-45, milestone N/A |
| `environment/Dockerfile` | #14-16, #20, #50 |
| `environment/requirements.txt` | #14, #20 blocker adjudication |
| `environment/docs/sfmt-spec.md` | #27, #55, spec alignment |
| `environment/src/format.c` | #17 stub design |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27-31, #52, spec alignment |
| `solution/solve.sh` | #21-23 |
| `entire-report.txt` | #32-39 rubric, #45, #54, agent stats, external adjudication |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: c-safe-format-spec/ ===
Summary: 0 error(s), 1 warning(s), 2 info
Task type detected: regular
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | Worst model |
| terminus-claude-opus-4-8 | 80.0% (4/5) | Best model |
| oracle | 100.0% (3/3) | Platform export |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — not a blocker |

Per-trial test pass ~93% in sufficiency analysis; binary reward means 0% task reward when grouped-zero-pad edge cases fail — fair given byte-exact contract.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `c-safe-format-spec`; regular layout; C security task |
| 1 Instruction | ☑ | Concise, absolute paths, normative spec ref, no hints |
| 2 Environment | ☑ | Digest-pinned base; tmux/asciinema; hash-locked pytest venv; no tests/solution in image |
| 3 Oracle | ☑ | Real C implementation; platform 100%; local not run (no Docker) |
| 4 Verifiers | ☑ | Canonical reward block; no runtime installs; 22 docstring tests; anti-cheat layers |
| 5 Metadata | ☑ | security/c tags fit; allow_internet=false |
| 6 Rubric | ☑ | Flat non-milestone format; 34/+ cap; 4 negatives; no test/metadata refs |
| 7 LLMaJ & agent evidence | ☑ | All quality checks pass; no systematic spec gaps |
| 8 Novelty & fairness | ☑ | Multi-step C implementation; cheating paths closed |
| 9 Long context | N/A | Not tagged long_context |

---

## 9. Reviewer note (copy-paste to portal)

Nice task overall. The sfmt contract is exceptionally clear, the held-out corpus and nonce round-trips make cheating impractical, and the environment is set up well with a pinned base and verifier deps baked into the image. Oracle passes cleanly and agent pass rates look right for medium difficulty — failures trace to grouped-zero-pad edge cases that are documented in the spec, not missing requirements. The platform rubric is correctly formatted as a flat non-milestone list at 34 positive points with four distinct negatives. I didn't find any blocking spec, test, or environment issues.

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
