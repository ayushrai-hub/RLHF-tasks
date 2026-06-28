# Terminus Review Report: go-avro-encode_v01.

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 46 |
| **UNCHECK count** | 9 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong Avro encoding repair task with excellent anti-cheat (hidden Python reference battery, SHA-pinned harness) and defensible Hard calibration (GPT-5.5 0%, Claude 80%). One real blocker: `test_pinned_contract_files_unmodified` enforces byte-for-byte SHA-256 on `main.go`, `types.go`, `schema.go`, and `go.mod`, but `instruction.md` never names those files or forbids editing/reformatting them — agents passed the encoding battery (10/10) yet failed grading (6/10 on pin check). Fix instruction disclosure or relax the verifier.

**Insights (concise):**

- `test_encode_battery_matches_contract`: 10/10 agent runs; `test_pinned_contract_files_unmodified`: 4/10 — failures are procedural, not encoding logic.
- LLMaJ `behavior_in_tests` over-maps "keep I/O format unchanged" to byte-identical harness files; instruction does not state that.
- Rubric uses optional `# Rubric 1` header on a non-milestone task — compliant per `docs/guidelines/rubrics.md` (not a blocker).
- `./src` in build commands fails absolute-path styling (#10) but is minor vs the pin gap.
- Oracle not run locally (Docker/Harbor unavailable in review session); `solution/solve.sh` only rewrites `varint.go`, `primitives.go`, `complex.go`, `encoder.go`.
- Worst-model 80% is at Easy-tier boundary but ≤80%, so #54 passes; `hard` defensible via best-model 0% per `difficulty.md`.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Verifier SHA-pins `main.go`, `types.go`, `schema.go`, `go.mod` byte-for-byte; instruction only says do not add/remove/rename files and keep stdin/stdout format unchanged — does not name immutable files or forbid edits/reformatting (`gofmt`). | `instruction.md:16-17`; `tests/test_outputs.py:31-36,51-57`; `entire-report.txt:39-42,52-58` (6/10 pin failures, 10/10 battery pass) | Add explicit bullet naming pinned files (`main.go`, `types.go`, `schema.go`, `go.mod`) and stating they must not be edited or reformatted; OR relax verifier to ignore whitespace-only diffs on those files. |

*Secondary (non-blocking alone):* `#10` — `go build ./src` / `go run ./src` use relative `./src` (`instruction.md:18`); prefer `/app/src`. Instruction Styling only.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Verifier SHA-pins harness files but instruction does not disclose byte-for-byte immutability; agents fail on `gofmt` despite correct encoder (ChatGPT High) | **Agree** | `instruction.md:16-17` vs `tests/test_outputs.py:31-36,51-57`; per-test rates in `entire-report.txt:39-42` |
| 2 | Non-milestone task uses milestone rubric format (`# Rubric 1`) | **Disagree** (not a blocker) | `docs/guidelines/rubrics.md:60` — `# Rubric 1` optional for non-milestone; only `# Rubric 2+` forbidden |
| 3 | LLMaJ `behavior_in_tests` PASS — pinned files covered by instruction | **Partially agree** | Pin check exists (`test_outputs.py:51-57`) but instruction "keep I/O format unchanged" does not equate to byte-identical `main.go`/`types.go`/`schema.go`/`go.mod` |
| 4 | Automated review READY TO USE; warnings are minor config | **Partially agree** | Structure sound; pin spec gap is material fairness issue automated review missed |
| 5 | `task.toml` non-standard fields (`category_profile`, `reference_pattern`) | **Agree** (informational) | `task.toml:19-21,37-38` — harmless extra fields, not a blocker |
| 6 | Verifier command `bash /app/tests/test.sh` non-standard vs `/tests/` | **Agree** (informational) | `task.toml:24`; `test.sh:4-6` resolves `HERE` relative to script — works, not a blocker |
| 7 | Difficulty Hard with Claude 80% / GPT-5.5 0% | **Agree** (calibration OK) | `entire-report.txt:26-27`; `difficulty.md:9-14` — best-model ≤20% supports `hard`; #54 not triggered at exactly 80% |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Four short paragraphs + one code block; within spirit of concise prompt | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Engineer tone; defers encoding rules to `/app/docs/` | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Light structure only | `instruction.md` |
| 4 | CHECK | No step by step instructions | States goal and constraints, not solve steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | Points to spec docs, no bug enumeration | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables in instruction | `instruction.md` |
| 7 | UNCHECK | Instruction is well specified | Pin immutability enforced by tests but not stated | `instruction.md:16-17`, `tests/test_outputs.py:51-57` |
| 8 | CHECK | Instruction is interesting | Real Avro binary encoding repair | — |
| 9 | CHECK | Instruction is unique | Avro zig-zag/block-framing task distinct from typical CLI tasks | — |
| 10 | UNCHECK | All paths in instruction are absolute | `go build ./src`, `go run ./src` use relative `./src` | `instruction.md:18` |
| 11 | CHECK | Task name does not appear in instruction.md | Title is "Avro binary encoder", not `go-avro-encode` | `instruction.md:1` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | Build-time apt/pip only | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies pinned with == | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5` | `environment/Dockerfile:23` |
| 15 | CHECK | Base Docker image pinned by digest | Both `FROM` lines `@sha256:` | `environment/Dockerfile:1,9` |
| 16 | CHECK | Environment does not use context outside environment/ | COPY limited to env tree | `environment/Dockerfile` |
| 17 | CHECK | Environment does not contain solution or ground truth | No solution/tests COPY; docs are contracts not answers | `environment/Dockerfile:26-30` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved mounts | No compose file | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install at runtime | pytest in image; test.sh only runs pytest | `environment/Dockerfile:23`, `tests/test.sh` |
| 21 | UNCHECK | Oracle passes consistently | Oracle not executed in this review session | — |
| 22 | CHECK | Oracle does not require internet | `solve.sh` rewrites local Go files only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Fixes encoder modules via implementation, not hardcoded hex | `solution/solve.sh:14-335` |
| 24 | CHECK | test.sh writes reward.txt on pass and fail | Canonical 0/1 block | `tests/test.sh:8-13` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | pytest all-or-nothing → 0/1 | `tests/test.sh` |
| 27 | UNCHECK | All tests aligned with instructions | Pin test enforces unstated byte-identical constraint | `tests/test_outputs.py:51-57`, `instruction.md:16-17` |
| 28 | CHECK | Tests check for correctness, not just format | Hidden battery compares status+hex to Python reference | `tests/test_outputs.py:82-95`, `tests/avro_ref.py` |
| 29 | CHECK | Tests verify behavior, not implementation | Runs built binary, no source grep | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Exact hex required for binary protocol correctness | `tests/test_outputs.py:82-95` |
| 31 | CHECK | Tests have informative names or docstrings | All four tests documented | `tests/test_outputs.py:44-95` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 9 distinct negatives in platform rubric | `entire-report.txt:315-323` |
| 33 | CHECK | Rubric scores from {1,2,3,5} | All lines use ±1,2,3,5 | `entire-report.txt:304-323` |
| 34 | CHECK | Each rubric criterion one line: Agent, comma, score | Format consistent | `entire-report.txt:304-323` |
| 35 | CHECK | Rubric criteria detailed and precise | Type-specific encoding behaviors named | `entire-report.txt:304-323` |
| 36 | CHECK | Rubric uses positive language for positives | Positives framed as recognition/behavior | `entire-report.txt:304-314` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path references | `entire-report.txt:304-323` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata/instruction refs | `entire-report.txt:304-323` |
| 39 | CHECK | Rubric does not mention oracle or NOP runs | No oracle/NOP mentions | `entire-report.txt:304-323` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task tree |
| 41 | CHECK | No unnecessary files in parent directory | Clean task root | task tree |
| 42 | CHECK | author_name and author_email present | Both `anonymous` | `task.toml:6-7` |
| 43 | CHECK | All other required metadata fields present | category, difficulty, timeouts, verifier | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | Go data-processing / serialization task | `task.toml:8-14` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `hard` defensible: best-model 0% ≤20% | `entire-report.txt:26-27`, `difficulty.md` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:15` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A — not milestone | `task.toml:15` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A — not milestone | `task.toml:15` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A — not milestone | `task.toml:15` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | No solution/ in image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify inputs to pass | Dynamic battery; pinned harness | `tests/avro_ref.py`, `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task not too easy (>80% worst model) | Worst-model 80% is not >80% | `entire-report.txt:26-27` |
| 55 | UNCHECK | Task not too hard or unfair | Undisclosed byte-pin constraint caused 6/10 false failures | `entire-report.txt:39-42,68-73` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 7, 10, 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Fix encoder to match `/app/docs/format.md` for every case | `test_encode_battery_matches_contract` | covered | `instruction.md:9-15`, `tests/test_outputs.py:82-95` |
| Do not add, remove, or rename files in `/app/src` | `test_source_file_set_unchanged` | covered | `instruction.md:16`, `tests/test_outputs.py:44-48` |
| Keep stdin/stdout JSON format unchanged | `test_pinned_contract_files_unmodified` (partial) | gap | Instruction says I/O format; test pins entire `main.go`/`types.go`/`schema.go`/`go.mod` bytes |
| `main.go`, `types.go`, `schema.go`, `go.mod` byte-identical | `test_pinned_contract_files_unmodified` | phantom | Not in `instruction.md` or env docs; only in verifier |
| Program builds with `go build ./src` | `test_program_builds` | covered | `instruction.md:18`, `tests/test_outputs.py:60-73` |
| Zig-zag, UTF-8 octet lengths, LE floats, blocks, field order, unions, fixed | `test_encode_battery_matches_contract` via `avro_ref.py` | covered | `environment/docs/format.md`, `tests/avro_ref.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #7, #10, blocker 1, spec alignment |
| `tests/test_outputs.py` | #27, #55, blocker 1, pin SHA table |
| `tests/test.sh` | #20, #24 |
| `tests/avro_ref.py` | #28, #52, anti-cheat |
| `task.toml` | #43, #45, #46-49 N/A |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `solution/solve.sh` | #22, #23 |
| `entire-report.txt` | agent stats, rubric, LLMaJ, ChatGPT adjudication |
| `docs/guidelines/rubrics.md` | rubric format (#32-39), milestone header claim |

---

## 7. Validation & agent performance

### Validation

```
=== Terminus Validation: go-avro-encode_v01. ===
Summary: 0 error(s), 1 warning(s), 1 info
WARNING: instruction.md may use relative paths — use absolute paths
INFO: non-milestone task (milestones preferred, not blocked)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Encoding hard for weaker model |
| terminus-claude-opus-4-8 | 80.0% (4/5) | At easy-tier ceiling |
| oracle | 100.0% (3/3) | Per platform report |
| nop | 0.0% (0/1) | Expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 80.0% |
| Observed tier (worst-model) | easy (boundary) |
| Declared difficulty | hard |
| Tier match (#45) | yes (best-model 0% supports hard) |

**Per-test pass rates** (`entire-report.txt:39-42`):

| Test | Pass rate | Implication |
|------|-----------|---------------|
| `test_source_file_set_unchanged` | 10/10 | File-set rule understood |
| `test_program_builds` | 10/10 | Builds succeed |
| `test_encode_battery_matches_contract` | 10/10 | Encoding logic solved |
| `test_pinned_contract_files_unmodified` | 4/10 | Undisclosed constraint drives failures |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Task `go-avro-encode`, regular (non-milestone), Go repair |
| 1 Instruction | ☑ | Pin gap confirmed; `./src` relative paths |
| 2 Environment | ☑ | Digest-pinned, tmux/asciinema, no tests/solution in image |
| 3 Oracle | ☐ | Not executed locally; static review of solve.sh OK |
| 4 Verifiers | ☑ | Canonical reward; pin test is fairness issue not broken harness |
| 5 Metadata | ☑ | Extra task.toml sections harmless |
| 6 Rubric | ☑ | Platform rubric valid; `# Rubric 1` OK for non-milestone |
| 7 LLMaJ & agent evidence | ☑ | Pin failure pattern confirmed in report |
| 8 Novelty & fairness | ☑ | Strong task; unfair only on undisclosed pin rule |
| 9 Long context | — | Not tagged |

---

## 9. Reviewer note (copy-paste to portal)

Really solid Avro encoding task — the hidden Python reference battery, digest-pinned Docker setup, and seeded bugs across zig-zag, endianness, blocks, and unions are all well done, and the difficulty calibration looks right with GPT-5.5 at 0%.

One fix before accept: grading SHA-checks `main.go`, `types.go`, `schema.go`, and `go.mod` for byte-for-byte identity, but the instructions only say not to add/remove/rename files and to keep the stdin/stdout JSON shape the same. Agents in the runs fixed the encoder and passed the full battery, then failed because routine `gofmt` or small harness edits tripped the pin check. Please either name those four files explicitly as read-only (no edits, no reformatting) or relax the verifier so cosmetic formatting-only changes do not fail an otherwise correct solution.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | yes | 1 (pin disclosure); secondary #10 |
| Rubric | no | — |
| Milestones | no | — |
| Task Difficulty | no | #45/#54 OK |
| Pinning Issues | no | Docker pins adequate |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Metadata Issues | no | — |
